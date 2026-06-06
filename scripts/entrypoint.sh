#!/usr/bin/env bash
set -euo pipefail

COMFYUI_TARBALL_URL="${COMFYUI_TARBALL_URL:-https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.tar.gz}"
COMFYUI_PATH="${COMFYUI_PATH:-/workspace/ComfyUI}"
VENV_PATH="${VENV_PATH:-/opt/venv}"
COMFYUI_ARGS="${COMFYUI_ARGS:---listen 0.0.0.0 --port 8188 --reserve-vram 1.0 --preview-method none --enable-manager --input-directory /workspace/ComfyUI/input --output-directory /workspace/ComfyUI/output --temp-directory /workspace/ComfyUI/temp --user-directory /workspace/ComfyUI/user}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-/usr/local/nvidia/lib:/usr/local/nvidia/lib64}"

mkdir -p "$COMFYUI_PATH"

if [ ! -f "$COMFYUI_PATH/main.py" ]; then
  echo "Downloading ComfyUI source into $COMFYUI_PATH"
  curl -L "$COMFYUI_TARBALL_URL" | tar -xz --strip-components=1 -C "$COMFYUI_PATH"
fi

export PATH="$VENV_PATH/bin:$PATH"

python - <<'PY'
import torch

print(f"PyTorch: {torch.__version__}")
print(f"PyTorch CUDA: {torch.version.cuda}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device count: {torch.cuda.device_count()}")
for index in range(torch.cuda.device_count()):
    print(f"CUDA device {index}: {torch.cuda.get_device_name(index)}")
PY

cd "$COMFYUI_PATH"
exec python main.py $COMFYUI_ARGS
