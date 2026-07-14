# Adapt AI

A hardware-aware local AI assistant. Adapt AI profiles your machine's RAM/VRAM,
recommends a locally-runnable Ollama model based on what your hardware can
actually handle, and gives you a full chat workspace: streaming responses,
file attachments, and in-browser Python execution.

Built by:

- Pulkit Sukhija ([@ManOfDiamond](https://github.com/ManOfDiamond))
- Aryan Sharma ([@Aryan5x](https://github.com/Aryan5x))
- Kaustabh Dua ([@coolbandariya](https://github.com/coolbandariya))
- Aishni Rathore ([@wildchord](https://github.com/wildchord))

## Problem statement

Running a local LLM sounds simple until you actually try it: pick the wrong
model and you either get an app that can't load ("out of memory") or one that
runs so slowly it's unusable. Most local-AI tutorials assume you already know
your GPU's VRAM, your model's memory footprint, and which quantization to
pick, and if you guess wrong, the failure mode is usually a cryptic OOM error
after a multi-gigabyte download.

## Solution overview

Adapt AI removes the guesswork. Before you download anything, it reads your
actual hardware (RAM, and VRAM if you have an NVIDIA GPU), scores your
machine's compatibility, and recommends a specific Ollama model sized to fit
what you have. From there it gives you a full local chat
workspace: streaming responses, live RAM/VRAM telemetry while you chat, file
attachments, and an in-browser Python execution sandbox, all running against
the model on your own machine.

## On-Device AI usage

All AI inference in Adapt AI runs locally through [Ollama](https://ollama.com),
which the backend manages directly on the user's machine:

- The FastAPI backend launches Ollama as a local subprocess automatically if
  it isn't already running (`start_ollama_if_needed` in `app.py`), and shuts
  it down when the app exits.
- On NVIDIA hardware, the app selects the strongest detected GPU and passes
  it to Ollama via `CUDA_VISIBLE_DEVICES`, so inference runs on-device on your
  own GPU rather than a remote server.
- Chat completions (`/api/chat`) and model downloads (`ollama.pull`) both go
  through the local Ollama Python client, no request containing your prompts
  or chat history is ever sent to a cloud AI API.
- Hardware profiling (`/api/benchmark`, `/api/metrics`) reads your system's
  RAM via `psutil` and VRAM via `GPUtil` (with an `nvidia-smi` fallback on
  Linux), entirely on-device, to decide which model you can realistically run.

The only network activity involved is the one-time model weights download
from Ollama's library the first time you pick a new model; after that,
every chat message and every code execution happens locally, offline-capable
once the model is on disk.

## What it does

1. **Scans your hardware:** reads live RAM and VRAM (NVIDIA GPUs, via GPUtil
   with an `nvidia-smi` fallback on Linux) and scores your machine's
   compatibility for running local LLMs.
2. **Recommends a model:** matches your available memory against a catalog of
   Ollama models, including Qwen 2.5, Gemma 2/3, Phi-3, Mistral, LLaVA,
   Llama 3.1, Llama 3.2, and Llama 3.2 Vision.
   The default recommendation is driven by VRAM bands.
3. **Live telemetry:** once you launch the workspace, RAM/VRAM usage is
   polled and charted in real time.
4. **Chat:** streams responses from your locally-running Ollama model, with
   file/image attachments, session history, and automatic context
   compression for long conversations.
5. **Code execution:** run Python directly from the chat interface and see
   the output inline.

## Stack

- **Backend:** FastAPI, Ollama (Python client), psutil, GPUtil, `nvidia-smi`
   fallback for Linux VRAM detection; when the app launches Ollama, it prefers
   the strongest detected NVIDIA dGPU via `CUDA_VISIBLE_DEVICES` and uses the
   GPU UUID when available.
- **Frontend:** Vanilla JS, Tailwind (CDN), Chart.js

## Running locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install [Ollama](https://ollama.com) and make sure it's running.
3. Start the backend:
   ```bash
   python app.py
   ```
   This runs on `http://0.0.0.0:8000` by default.
   If Ollama is not already running, the app will start it automatically and
   shut it down when the server exits.
4. `index.html` opens automatically in your default browser after startup.

## API

| Route              | Method | Purpose                                                 |
|--------------------|--------|---------------------------------------------------------|
| `/api/metrics`     | GET    | Live RAM/VRAM usage                                     |
| `/api/benchmark`   | GET    | Hardware compatibility score + model recommendation     |
| `/api/chat`        | POST   | Streaming chat completion via Ollama (SSE)              |
| `/api/execute`     | POST   | Runs submitted Python code and returns captured output  |

## Credits

- **[Ollama](https://ollama.com)** — local model runtime and Python client
  this app is built on.
- **[FastAPI](https://fastapi.tiangolo.com/)** — backend web framework.
- **[Chart.js](https://www.chartjs.org/)** — live telemetry graph.
- **[psutil](https://github.com/giampaolo/psutil)** / **[GPUtil](https://github.com/anderskm/gputil)** — hardware metrics.

## Model licenses

Adapt AI does not bundle or redistribute any model weights. It recommends a
model based on your hardware, and Ollama downloads it directly from the
model's own source the first time you use it. The license for each model you
choose to pull is between you and its publisher:

| Model tag | Publisher | License |
|-----------|-----------|---------|
| `qwen2.5:0.5b` | Alibaba | [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| `qwen2.5:1.5b` | Alibaba | [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| `gemma2:2b` | Google | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| `gemma2:9b` | Google | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| `gemma3:4b` | Google | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| `phi3:mini` | Microsoft | [MIT](https://opensource.org/license/mit/) |
| `mistral:7b` | Mistral AI | [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| `llava:7b` | Community | [Llama 2 Community License](https://www.llama.com/llama2/license/) |
| `llava:13b` | Community | [Llama 2 Community License](https://www.llama.com/llama2/license/) |
| `llama3.1:8b` | Meta | [Llama 3.1 Community License](https://www.llama.com/llama3_1/license/) |
| `llama3.2:1b` | Meta | [Llama 3.2 Community License](https://www.llama.com/llama3_2/license/) |
| `llama3.2:3b` | Meta | [Llama 3.2 Community License](https://www.llama.com/llama3_2/license/) |
| `llama3.2-vision` | Meta | [Llama 3.2 Community License](https://www.llama.com/llama3_2/license/) |

The Llama Community Licenses require attribution ("Built with Llama") if you
redistribute the models or a system built on their outputs — see the linked
license text for the exact terms before deploying beyond a local demo. Gemma is
also subject to Google's Gemma terms, so check those terms before using it in a
redistributed product.

## Model catalog

These are the model tags exposed in the app, along with the approximate Ollama
download size reported by the upstream library pages:

| Model tag | Size | Notes |
|-----------|------|-------|
| `qwen2.5:0.5b` | 398 MB | Smallest general-purpose option |
| `qwen2.5:1.5b` | 986 MB | Lightweight chat model |
| `gemma2:2b` | 1.6 GB | Compact Gemma 2 variant |
| `gemma3:4b` | 3.3 GB | Multimodal Gemma 3 model for image understanding |
| `phi3:mini` | 2.2 GB | Microsoft Phi-3 Mini |
| `llama3.2:1b` | 1.3 GB | Small Llama 3.2 text model |
| `llama3.2:3b` | 2.0 GB | Default Llama 3.2 text model |
| `mistral:7b` | 4.4 GB | Strong 7B text model |
| `llava:7b` | 4.7 GB | Smaller vision-language model |
| `llama3.1:8b` | 4.9 GB | Larger general-purpose model |
| `llava:13b` | 8.0 GB | Larger vision-language model |
| `gemma2:9b` | 5.4 GB | Heavier text model |
| `llama3.2-vision` | 7.8 GB | Multimodal image reasoning model for image understanding; best fit for 8 GB-class GPUs |

## Known limitation(s)
- `/api/execute` runs code in an isolated subprocess with a 5-second timeout
  and a blocklist on `open`/`input`/`exit`/`quit`, and CORS is restricted to
  the app's own local origins. It's still not a full sandbox.
- Model downloads happen on first use if the recommended model isn't already
  pulled locally, which can take a while depending on model size and
  connection speed.

## License

Apache-2.0 — see [LICENSE](LICENSE).
