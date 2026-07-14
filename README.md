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

## What it does

1. **Scans your hardware:** reads live RAM and VRAM (NVIDIA GPUs, via GPUtil
   with an `nvidia-smi` fallback on Linux) and scores your machine's
   compatibility for running local LLMs.
2. **Recommends a model:** matches your available memory against a small
   catalog of Ollama models, from Qwen 2.5 (0.5B) up to Llama 3.2 Vision (11B).
3. **Live telemetry:** once you launch the workspace, RAM/VRAM usage is
   polled and charted in real time.
4. **Chat:** streams responses from your locally-running Ollama model, with
   file/image attachments, session history, and automatic context
   compression for long conversations.
5. **Code execution:** run Python directly from the chat interface and see
   the output inline.

## Stack

- **Backend:** FastAPI, Ollama (Python client), psutil, GPUtil, `nvidia-smi`
   fallback for Linux VRAM detection
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
4. Open `index.html` in a browser.

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

| Model                  | Publisher   | License                                                                  |
|------------------------|-------------|--------------------------------------------------------------------------|
| Qwen 2.5 (0.5B)        | Alibaba     | [Apache 2.0](https://huggingface.co/Qwen/Qwen2.5-0.5B/blob/main/LICENSE) |
| Llama 3.2 (1B, 3B)     | Meta        | [Llama 3.2 Community License](https://www.llama.com/llama3_2/license/)   |
| Llama 3.1 (8B)         | Meta        | [Llama 3.1 Community License](https://www.llama.com/llama3_1/license/)   |
| Llama 3.2 Vision (11B) | Meta        | [Llama 3.2 Community License](https://www.llama.com/llama3_2/license/)   |

The Llama Community Licenses require attribution ("Built with Llama") if you
redistribute the models or a system built on their outputs — see the linked
license text for the exact terms before deploying beyond a local demo.

## Known limitation(s)
- Model downloads happen on first use if the recommended model isn't already
  pulled locally, which can take a while depending on model size and
  connection speed.

## License

Apache-2.0 — see [LICENSE](LICENSE).
