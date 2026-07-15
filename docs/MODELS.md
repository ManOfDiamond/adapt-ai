# Model Reference

Adapt AI does not bundle or redistribute any model weights. It recommends a
model based on your hardware, and Ollama downloads it directly from the
model's own source the first time you use it. The license for each model you
choose to pull is between you and its publisher.

## Model licenses

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
license text for the exact terms before deploying beyond a local demo. Gemma
is also subject to Google's Gemma terms, so check those terms before using it
in a redistributed product.

## Model catalog

These are the model tags exposed in the app, along with the approximate
Ollama download size reported by the upstream library pages:

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
