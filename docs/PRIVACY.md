# Local AI Verification, Privacy, and Safety

## What runs on-device

- **Chat inference:** every chat completion (`/api/chat`) is served by a
  locally-running Ollama process on your own machine. No prompt, response,
  or chat history is sent to any cloud AI API.
- **Hardware profiling:** `/api/metrics` and `/api/benchmark` read your
  system's own RAM (`psutil`) and VRAM (`GPUtil`, with an `nvidia-smi`
  fallback on Linux) directly from the host machine.
- **Code execution:** `/api/execute` runs submitted Python in a local
  subprocess on your machine; the code and its output never leave the host.

## What requires internet

- **Model downloads:** The first time you select a model that isn't already
  pulled, Ollama downloads its weights from its own model library. This is
  the only outbound network call the app makes as part of its core
  functionality. Once a model is on disk, chatting with it works fully
  offline.

## Does any user data leave the device?

No. Chat messages, attached files, executed code, and hardware telemetry all
stay local. The app does not call any third-party analytics, logging, or AI
API service.

## Data handling and storage

- Chat session history is kept in the browser's in-memory JS state for the
  current session; it is not written to disk by the backend and is not
  persisted anywhere once the browser tab is closed, beyond what the browser
  itself may cache.
- `/api/execute` does not write submitted code to disk, it's passed directly
  to a subprocess and discarded after execution.
- No user accounts, authentication, or telemetry collection exist in this
  project.

## Permissions

The app itself doesn't request any OS-level permissions beyond what a normal
local web server and subprocess launcher need (opening a port, spawning
`ollama` and `python` subprocesses). File attachments in chat are handled
client-side in the browser; see `js/app.js` for exactly how attached files
are read and sent to `/api/chat`.

## Known risks

See the "Known limitation(s)" section in [README.md](README.md) for the
current state of `/api/execute`'s sandboxing and CORS configuration, the
short version is that code execution is isolated in a subprocess with a
timeout, but it is not a full container-level sandbox, so this project should
be run locally and not exposed on a shared or public network.
