# ComfyUI CUDA 13 Docker

Dual-worker ComfyUI setup for NVIDIA GPUs using PyTorch CUDA 13 wheels.

## Layout

- ComfyUI source is baked into the image
- `models/`: persistent model folders
- `inputs/`: files visible in ComfyUI's input directory
- `outputs/gpu0/`, `outputs/gpu1/`: generated files from each worker
- `user/gpu0/`, `user/gpu1/`: separate ComfyUI user settings and databases
- `temp/gpu0/`, `temp/gpu1/`: separate runtime temp folders

The image installs:

- ComfyUI from `COMFYUI_TARBALL_URL`
- `comfyui_manager==4.2.1` through ComfyUI's `manager_requirements.txt`
- `ComfyUI-MultiGPU` at `b51c99a525e9607e43545ee2a8b7694c74a4775a`

## Start

```bash
docker compose up --build
```

ComfyUI will be available at:

```text
http://localhost:8188  # GPU 0 worker
http://localhost:8189  # GPU 1 worker
```

Each worker is pinned with both Docker GPU device requests and `CUDA_VISIBLE_DEVICES`. The single-GPU workers intentionally do not pass `--cuda-device` or `--default-device`, because ComfyUI rewrites `CUDA_VISIBLE_DEVICES` from those flags. Inside each worker, PyTorch remaps the selected physical GPU to CUDA device `0`, so both workers launch with:

```text
--reserve-vram 1.0 --preview-method none
```

Override them by setting `COMFYUI_ARGS` in `docker-compose.yml`.

## Sharded Worker

For one oversized workflow that needs both GPUs through MultiGPU/DisTorch nodes, start the optional sharded profile:

```bash
docker compose --profile sharded up comfyui-sharded
```

It serves `http://localhost:8190` and launches with `--cuda-device 0,1 --default-device 0`.

Do not run it alongside the two default workers unless you intentionally want all services to contend for VRAM.

## GPU Preflight

Run this from the project directory to confirm Docker can see the GPUs:

```bash
docker run --rm --gpus all nvidia/cuda:13.0.0-runtime-ubuntu24.04 nvidia-smi
```

On startup, the container prints the PyTorch version, CUDA runtime version, CUDA availability, and every visible CUDA device.

After the workers are running, run:

```bash
scripts/cuda-smoke.sh
scripts/api-smoke.sh
python3 scripts/wan-parallel-smoke.py
```

`cuda-smoke.sh` runs FP32 and FP16 PyTorch matmul in each worker. `api-smoke.sh` checks `/system_stats` and selected node registrations. The Wan script queues a minimal API prompt concurrently against both workers and uses the Wan 2.2 filenames present under `models/`.
