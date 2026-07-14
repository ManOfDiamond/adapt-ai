import atexit
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import ollama
import psutil
import json
import io
import os
import time
from pathlib import Path
import subprocess
from contextlib import redirect_stdout
from contextlib import asynccontextmanager
from typing import Optional
import webbrowser
import socket
import platform

try:
    import GPUtil
except ImportError:
    GPUtil = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await launch_app_side_effects()
        yield
    finally:
        stop_ollama_if_started()


app = FastAPI(lifespan=lifespan)

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
INDEX_HTML_PATH = Path(__file__).with_name("index.html").resolve()

_ollama_process: subprocess.Popen | None = None
_ollama_started_by_app = False
_browser_opened = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatPayload(BaseModel):
    model: str
    messages: list
    options: Optional[dict] = None

class CodePayload(BaseModel):
    code: str


def is_ollama_running() -> bool:
    try:
        with socket.create_connection((OLLAMA_HOST, OLLAMA_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def get_preferred_cuda_visible_devices() -> Optional[str]:
    if GPUtil:
        gpus = GPUtil.getGPUs()
        if gpus:
            preferred_gpu = max(gpus, key=lambda gpu: gpu.memoryTotal)
            preferred_uuid = getattr(preferred_gpu, "uuid", None)
            if preferred_uuid:
                return str(preferred_uuid)
            return str(preferred_gpu.id)

    try:
        nvidia_smi = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,uuid,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        preferred_uuid = None
        preferred_index = None
        preferred_memory = -1.0
        for line in nvidia_smi.stdout.splitlines():
            if not line.strip():
                continue
            gpu_index, gpu_uuid, memory_total = [part.strip() for part in line.split(",")[:3]]
            total_gb = float(memory_total) / 1024.0
            if total_gb > preferred_memory:
                preferred_memory = total_gb
                preferred_uuid = gpu_uuid
                preferred_index = gpu_index
        if preferred_uuid:
            return preferred_uuid
        if preferred_index is not None:
            return preferred_index
    except Exception:
        pass

    return None


def stop_external_ollama_processes() -> None:
    current_pid = os.getpid()
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if process.info["pid"] == current_pid:
                continue

            process_name = (process.info.get("name") or "").lower()
            process_cmdline = " ".join(process.info.get("cmdline") or []).lower()
            if "ollama" not in process_name and "ollama" not in process_cmdline:
                continue

            process.terminate()
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def start_ollama_if_needed(force_restart: bool = False) -> bool:
    global _ollama_process, _ollama_started_by_app

    if is_ollama_running():
        if not force_restart:
            return False
        stop_external_ollama_processes()
        for _ in range(20):
            if not is_ollama_running():
                break
            time.sleep(0.25)
        if is_ollama_running():
            return False

    launch_env = os.environ.copy()
    if "CUDA_VISIBLE_DEVICES" not in launch_env:
        preferred_cuda_devices = get_preferred_cuda_visible_devices()
        if preferred_cuda_devices is not None:
            launch_env["CUDA_VISIBLE_DEVICES"] = preferred_cuda_devices
    launch_env.setdefault("OLLAMA_FLASH_ATTENTION", "1")
    launch_env.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
    launch_env.setdefault("OLLAMA_NUM_PARALLEL", "1")

    if platform.system() == "Windows":
        _ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=launch_env,
        )
    else:
        _ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=launch_env,
        )
    _ollama_started_by_app = True
    return True


async def wait_for_ollama_ready(timeout_seconds: float = 10.0) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while loop.time() < deadline:
        if is_ollama_running():
            return True
        if _ollama_process is not None and _ollama_process.poll() is not None:
            break
        await asyncio.sleep(0.25)
    return is_ollama_running()


def stop_ollama_if_started() -> None:
    global _ollama_process, _ollama_started_by_app

    if not _ollama_started_by_app or _ollama_process is None:
        return

    if _ollama_process.poll() is None:
        _ollama_process.terminate()
        try:
            _ollama_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _ollama_process.kill()
    _ollama_process = None
    _ollama_started_by_app = False


def open_index_html() -> None:
    global _browser_opened

    if _browser_opened:
        return

    webbrowser.open(INDEX_HTML_PATH.as_uri(), new=1, autoraise=True)
    _browser_opened = True


async def launch_app_side_effects() -> None:
    try:
        start_ollama_if_needed(force_restart=True)
        await wait_for_ollama_ready()
    except FileNotFoundError:
        print("[Adapt AI] Warning: Ollama binary not found on PATH.")

    await asyncio.sleep(0.5)
    open_index_html()


atexit.register(stop_ollama_if_started)

def get_memory_stats():
    vm = psutil.virtual_memory()
    stats = {
        "total_ram_gb": round(vm.total / (1024 ** 3), 2),
        "available_ram_gb": round(vm.available / (1024 ** 3), 2),
        "used_ram_gb": round((vm.total - vm.available) / (1024 ** 3), 2),
        "gpu_total_vram_gb": 0.0,
        "gpu_free_vram_gb": 0.0,
        "gpu_used_vram_gb": 0.0,
        "has_gpu": False
    }

    def apply_gpu_stats(memory_total_mb, memory_free_mb, memory_used_mb):
        stats["gpu_total_vram_gb"] = round(memory_total_mb / 1024.0, 2)
        stats["gpu_free_vram_gb"] = round(memory_free_mb / 1024.0, 2)
        stats["gpu_used_vram_gb"] = round(memory_used_mb / 1024.0, 2)
        stats["has_gpu"] = True

    try:
        if GPUtil:
            gpus = GPUtil.getGPUs()
            if gpus and len(gpus) > 0:
                apply_gpu_stats(gpus[0].memoryTotal, gpus[0].memoryFree, gpus[0].memoryUsed)
                return stats

        nvidia_smi = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.free,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        first_gpu = next((line.strip() for line in nvidia_smi.stdout.splitlines() if line.strip()), None)
        if first_gpu:
            memory_total_mb, memory_free_mb, memory_used_mb = [float(value.strip()) for value in first_gpu.split(",")[:3]]
            apply_gpu_stats(memory_total_mb, memory_free_mb, memory_used_mb)
    except Exception as e:
        stats["has_gpu"] = False
    return stats

def calculate_compatibility_score(stats):
    score = 0
    ram = stats["total_ram_gb"]
    if ram >= 32: score += 40
    elif ram >= 16: score += 30
    elif ram >= 8: score += 15
    else: score += 5

    if stats["has_gpu"]:
        vram = stats["gpu_total_vram_gb"]
        if vram >= 12: score += 60
        elif vram >= 8: score += 45
        elif vram >= 4: score += 30
        else: score += 15
    else:
        score = max(5, score - 10)
    return min(score, 100)


AVAILABLE_MODELS = [
    {"id": "qwen2.5:0.5b", "name": "Qwen 2.5 (0.5B)", "min_gb": 1.0},
    {"id": "qwen2.5:1.5b", "name": "Qwen 2.5 (1.5B)", "min_gb": 2.5},
    {"id": "gemma2:2b", "name": "Gemma 2 (2B)", "min_gb": 3.0},
    {"id": "llama3.2:1b", "name": "Llama 3.2 (1B)", "min_gb": 2.0},
    {"id": "phi3:mini", "name": "Phi-3 Mini", "min_gb": 3.5},
    {"id": "llama3.2:3b", "name": "Llama 3.2 (3B)", "min_gb": 5.0},
    {"id": "mistral:7b", "name": "Mistral (7B)", "min_gb": 8.0},
    {"id": "llava:7b", "name": "LLaVA (7B) - Image Understanding", "min_gb": 5.0},
    {"id": "gemma3:4b", "name": "Gemma 3 (4B) - Image Understanding", "min_gb": 5.5},
    {"id": "llama3.1:8b", "name": "Llama 3.1 (8B)", "min_gb": 9.0},
    {"id": "llava:13b", "name": "LLaVA (13B) - Image Understanding", "min_gb": 9.0},
    {"id": "gemma2:9b", "name": "Gemma 2 (9B)", "min_gb": 10.0},
    {"id": "llama3.2-vision", "name": "Llama 3.2 Vision (11B) - Image Understanding", "min_gb": 7.5},
]

VRAM_RECOMMENDATION_BANDS = [
    {"min_gb": 0.0, "max_gb": 1.5, "model_id": "qwen2.5:0.5b"},
    {"min_gb": 1.5, "max_gb": 2.5, "model_id": "qwen2.5:1.5b"},
    {"min_gb": 2.5, "max_gb": 3.5, "model_id": "llama3.2:1b"},
    {"min_gb": 3.5, "max_gb": 4.5, "model_id": "phi3:mini"},
    {"min_gb": 4.5, "max_gb": 5.5, "model_id": "llama3.2:3b"},
    {"min_gb": 5.5, "max_gb": 7.5, "model_id": "mistral:7b"},
    {"min_gb": 7.5, "max_gb": 9.0, "model_id": "mistral:7b"},
    {"min_gb": 9.0, "max_gb": 10.0, "model_id": "llama3.1:8b"},
    {"min_gb": 10.0, "max_gb": 12.0, "model_id": "gemma2:9b"},
    {"min_gb": 12.0, "max_gb": float("inf"), "model_id": "gemma2:9b"},
]


def recommend_model_for_vram(vram_gb: float) -> str:
    for band in VRAM_RECOMMENDATION_BANDS:
        if band["min_gb"] <= vram_gb < band["max_gb"]:
            return band["model_id"]
    return "qwen2.5:0.5b"

@app.get("/api/benchmark")
async def benchmark_hardware():
    try:
        mem_stats = get_memory_stats()
        
        primary_vram = mem_stats["gpu_total_vram_gb"] if mem_stats["has_gpu"] else (mem_stats["total_ram_gb"] * 0.5)
        compatibility_score = calculate_compatibility_score(mem_stats)

        recommended_model = recommend_model_for_vram(primary_vram)

        return {
            "safe": True,
            "compatibility_score": compatibility_score,
            "memory": mem_stats,
            "recommendation": recommended_model,
            "catalog": AVAILABLE_MODELS
        }
    except Exception as e:
        return {"safe": False, "reason": "Ollama not running."}

@app.get("/api/metrics")
async def get_live_metrics():
    return get_memory_stats()

@app.post("/api/execute")
async def execute_python_code(payload: CodePayload):
    output_buffer = io.StringIO()
    try:
        with redirect_stdout(output_buffer):
            exec_globals = {}
            exec(payload.code, exec_globals)
        result = output_buffer.getvalue()
        if not result.strip():
            result = "[Execution Successful: No terminal output returned.]"
        return {"success": True, "output": result}
    except Exception as e:
        return {"success": False, "output": f"Runtime Error: {str(e)}"}

def compress_context_safeguard(messages: list) -> list:
    def estimate_tokens(msg): 
        text_tokens = len(msg.get('content', '').split()) * 1.3
        image_penalty = 1000 if msg.get('images') else 0 
        return text_tokens + image_penalty

    total_tokens = sum(estimate_tokens(msg) for msg in messages)
    
    if total_tokens > 2000 and len(messages) > 3:
        system_prompt = messages[0]
        recent_conversation = messages[-4:] 
        return [system_prompt, {"role": "user", "content": "[Context compressed.]"}, *recent_conversation]
    return messages

@app.post("/api/chat")
async def chat_stream(payload: ChatPayload):
    safe_messages = compress_context_safeguard(payload.messages)
    
    chat_options = {}
    options = payload.options or {}
    if options.get("num_ctx") is not None:
        chat_options["num_ctx"] = options["num_ctx"]

    async def event_generator():
        try:
            ollama.show(payload.model)
        except ollama.ResponseError:
            print(f"\n[Adapt AI] Model '{payload.model}' not found locally. Initiating background pull...")
            
            newline = "\n"
            msg = f"*(Downloading `{payload.model}` in VS Code terminal. Please wait...)*{newline}{newline}"
            yield f"data: {json.dumps({'content': msg})}\n\n"
            
            try:
                for progress in ollama.pull(payload.model, stream=True):
                    status = progress.get('status', '')
                    completed = progress.get('completed')
                    total = progress.get('total')
                    
                    if total is not None and completed is not None and total > 0:
                        percent = int((completed / total) * 100)
                        print(f"\rDownloading: {status} [{percent}%]", end="", flush=True)
                    else:
                        print(f"\rDownloading: {status}", end="", flush=True)
                print(f"\n[Adapt AI] Model '{payload.model}' successfully downloaded!\n")
            except Exception as e:
                print(f"\n[Adapt AI] Warning: Pull interrupted: {e}")
                yield f"data: {json.dumps({'content': '⚠️ Model download failed. Check VS Code terminal.'})}\n\n"
                return 

        try:
            stream = ollama.chat(model=payload.model, messages=safe_messages, stream=True, options=chat_options)
            for chunk in stream:
                yield f"data: {json.dumps({'content': chunk['message']['content']})}\n\n"
        except Exception as e:
            print(f"[Backend Error] Ollama stream failed: {e}")
            error_msg = "⚠️ **System Alert:** The model failed to load. Ensure Ollama is running and you have sufficient VRAM."
            yield f"data: {json.dumps({'content': error_msg})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)