# Technical Report

## Model and runtime

Adapt AI does not ship a fixed model — it recommends one of several Ollama
models based on the host machine's detected RAM/VRAM (see
[MODELS.md](MODELS.md) for the full catalog). All inference runs through the
[Ollama](https://ollama.com) runtime, which the backend launches and manages
directly (`start_ollama_if_needed` in `app.py`).

Ollama serves models in **GGUF** format, running on `llama.cpp` under the
hood, with automatic GPU offload when a supported NVIDIA GPU is detected
(the backend passes the preferred GPU via `CUDA_VISIBLE_DEVICES`) and CPU
fallback otherwise.

## Quantization

Adapt AI does not perform its own quantization — it relies on the
pre-quantized GGUF builds Ollama pulls from its model library, typically
**Q4_K_M** (4-bit) by default for the model tags in this app's catalog
unless a different quantization is specified in the model tag itself. This
keeps download size and VRAM/RAM footprint low without a separate
quantization step in this project's own code.

## Model size

See [MODELS.md](MODELS.md) for the full table. Sizes range from **398 MB**
(`qwen2.5:0.5b`) up to **8.0 GB** (`llava:13b`), covering everything from
low-RAM laptops to 8 GB-class GPUs.

## Tested device

| Field | Value |
|---|---|
| CPU | AMD Ryzen 7 7840HS w/ Radeon 780M Graphics |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8 GB VRAM |
| RAM | 16 GB |
| OS | Arch Linux (CachyOS kernel) |
| Ollama | 0.32.0, with the `ollama-cuda13-bin` package for CUDA 13 support |

## Inference latency

Measured with `ollama run <model> "Explain photosynthesis in two sentences." --verbose`,
one run per model, on the device above with the model fully offloaded to
GPU (`ollama ps` confirmed `100% GPU` for every row below). Time to first
token is `load duration + prompt eval duration` from Ollama's own reported
figures.

| Model | Tokens/sec | Time to first token |
|---|---|---|
| `qwen2.5:0.5b` | 314.55 | ~0.15s |
| `qwen2.5:1.5b` | 163.48 | ~0.15s |
| `gemma2:2b` | 105.61 | ~0.20s |
| `llama3.2:1b` | 156.54 | ~2.10s |
| `llama3.2:3b` | 94.58 | ~2.13s |
| `gemma3:4b` | 75.47 | ~5.00s |
| `llava:7b` | 55.62 | ~3.00s |
| `mistral:7b` | 51.94 | ~2.64s |
| `llama3.1:8b` | 49.21 | ~3.66s |
| `phi3:mini` | 94.21 | ~8.74s |
| `gemma2:9b` | 40.15 | ~6.99s |

`llava:13b` and `llama3.2-vision` were not benchmarked (large downloads,
skipped for time). All other catalog models were run to completion.

A few things worth noting in this data:

- **Throughput generally decreases with model size**, as expected — the
  0.5B model runs at over 300 tokens/sec, while the 9B model runs at ~40.
- **`phi3:mini`'s time to first token (~8.74s) is an outlier** relative to
  its size — its `prompt eval duration` alone was 3.37s, far higher than
  any other model's prompt-eval time even among larger models. This looks
  like a one-off (possibly a cold cache or first-load effect on this
  particular run) rather than a property of the model itself, since a
  repeat run would be needed to confirm it's reproducible.
- **`gemma3:4b` and `gemma2:9b` both show multi-second load times**
  (4.88s and 6.85s respectively) even though they aren't the largest models
  in the catalog, likely reflecting real differences in how those model
  files are structured/loaded rather than pure parameter count.

Reproduce this table yourself with [`benchmark_models.sh`](benchmark_models.sh),
which runs every catalog model once and writes a markdown table with these
same columns.

### A real GPU-detection issue found during benchmarking

On first setup on Linux, `ollama ps` reported `100% CPU` for this exact GPU
despite `nvidia-smi` showing the card and free VRAM correctly. The cause was
that the base `ollama` package (as installed via the distro's package
manager) did not include the CUDA backend library — a separate
`ollama-cuda13-bin` package was required to enable GPU offload, since the
system's driver reported CUDA 13.3 and the base package's bundled runtime
didn't include a matching backend. After installing it, `ollama ps`
correctly reported `100% GPU`, and throughput improved accordingly. Worth
checking `ollama ps` after any fresh install, since Ollama falls back to CPU
silently rather than erroring when its CUDA backend isn't present.

## Evaluation

Adapt AI is an orchestration and hardware-profiling tool built on top of
existing, pre-trained open models — it does not train, fine-tune, or modify
any model's weights, so traditional accuracy/quality benchmarking (e.g.
against a held-out dataset) doesn't directly apply to the project itself.

The parts of the system that are meaningfully evaluable are:

- **Hardware compatibility scoring** — `calculate_compatibility_score` in
  `app.py` is a deterministic, rule-based function (RAM/VRAM thresholds
  mapped to a 0–100 score), not a learned model, so it can be checked for
  correctness directly rather than benchmarked statistically. Given known
  RAM/VRAM inputs, the score is fully reproducible.
- **Model recommendation** — `recommend_model_for_vram` maps detected VRAM
  to a specific model tag using fixed bands (see [MODELS.md](MODELS.md)).
  The tested device above (8 GB VRAM) was recommended `mistral:7b`, which
  the latency table confirms loads and runs successfully at ~52 tokens/sec
  with full GPU offload — the recommendation held up in practice.
- **Chat quality** — inherited entirely from whichever upstream Ollama model
  is selected (Qwen 2.5, Gemma, Phi-3, Mistral, Llama, LLaVA); Adapt AI does
  not alter model outputs beyond the context-compression safeguard in
  `compress_context_safeguard`, so model-quality evaluation would really be
  an evaluation of those upstream models, not of this project.

### Known failure cases

- If a model is recommended based on total VRAM but another process is
  already using a significant chunk of it, the load can still fail with an
  out-of-memory error from Ollama — the app reads free/total VRAM at scan
  time but doesn't re-check immediately before a model load.
- `compress_context_safeguard`'s token estimate is a rough heuristic
  (`words * 1.3`, plus a flat penalty for image attachments), not an exact
  tokenizer count, so very long non-English or code-heavy conversations
  could be compressed later or earlier than an exact count would suggest.
- Without the correct CUDA backend package installed (see the GPU-detection
  note above), Ollama silently runs on CPU instead of the intended GPU —
  the app's own hardware scan doesn't currently detect or warn about this
  case, since it checks VRAM availability via `nvidia-smi`/`GPUtil`
  independent of whether Ollama itself can actually use the GPU.
