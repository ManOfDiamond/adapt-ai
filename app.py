from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import ollama
import psutil
import json
import io
import os
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
    try:
        if GPUtil:
            gpus = GPUtil.getGPUs()
            if gpus and len(gpus) > 0:
                stats["gpu_total_vram_gb"] = round(gpus[0].memoryTotal / 1024.0, 2)
                stats["gpu_free_vram_gb"] = round(gpus[0].memoryFree / 1024.0, 2)
                stats["gpu_used_vram_gb"] = round(gpus[0].memoryUsed / 1024.0, 2)
                stats["has_gpu"] = True
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)