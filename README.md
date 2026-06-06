# ComfyUI CUDA 13 Docker

Single-container ComfyUI setup for NVIDIA GPUs using CUDA 13.0 and PyTorch cu130 wheels.

## Layout

- `app/`: mounted ComfyUI source tree, downloaded automatically on first start if empty
- `models/`: persistent model folders
- `inputs/`: files visible in ComfyUI's input directory
- `outputs/`: generated files
- `custom_nodes/`: persistent custom nodes
- `user/`: persistent ComfyUI user settings and database

## Start

```bash
docker compose up --build
```

ComfyUI will be available at:

```text
http://localhost:8188
```

The default launch arguments expose both GPUs and select GPU 0 as the default device:

```text
--listen 0.0.0.0 --port 8188 --cuda-device 0,1 --default-device 0
```

Override them by setting `COMFYUI_ARGS` in `docker-compose.yml`.

## GPU Preflight

Run this from the project directory to confirm Docker can see the GPUs:

```bash
docker run --rm --gpus all nvidia/cuda:13.0.0-runtime-ubuntu24.04 nvidia-smi
```

On startup, the container prints the PyTorch version, CUDA runtime version, CUDA availability, and every visible CUDA device.
