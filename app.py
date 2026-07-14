from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import ollama
import psutil
import json
import io
import os
import subprocess
from contextlib import redirect_stdout
from typing import Optional

try:
    import GPUtil
except ImportError:
    GPUtil = None

app = FastAPI()

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

@app.get("/api/benchmark")
async def benchmark_hardware():
    try:
        mem_stats = get_memory_stats()
        
        available_models = [
            {"id": "qwen2.5:0.5b", "name": "Qwen 2.5 (0.5B)", "min_gb": 1.0},
            {"id": "llama3.2:1b", "name": "Llama 3.2 (1B)", "min_gb": 2.0},
            {"id": "llama3.2:3b", "name": "Llama 3.2 (3B)", "min_gb": 5.0},
            {"id": "llama3.1:8b", "name": "Llama 3.1 (8B)", "min_gb": 9.0},
            {"id": "llama3.2-vision", "name": "Llama 3.2 Vision (11B) - Photos", "min_gb": 10.0}
        ]
        
        primary_memory = mem_stats["gpu_total_vram_gb"] if mem_stats["has_gpu"] else (mem_stats["total_ram_gb"] * 0.5)
        compatibility_score = calculate_compatibility_score(mem_stats)
        
        if primary_memory >= 10.0: recommended_model = "llama3.2-vision"
        elif primary_memory >= 9.0: recommended_model = "llama3.1:8b"
        elif primary_memory >= 5.0: recommended_model = "llama3.2:3b"
        elif primary_memory >= 2.0: recommended_model = "llama3.2:1b"
        else: recommended_model = "qwen2.5:0.5b"

        return {
            "safe": True,
            "compatibility_score": compatibility_score,
            "memory": mem_stats,
            "recommendation": recommended_model,
            "catalog": available_models
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
    if getattr(payload, "options", None):
        if "num_ctx" in payload.options and payload.options["num_ctx"] is not None:
            chat_options["num_ctx"] = payload.options["num_ctx"]

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