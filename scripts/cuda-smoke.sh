#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 0 ]; then
  services=("$@")
else
  services=(comfyui-gpu0 comfyui-gpu1)
fi

for service in "${services[@]}"; do
  echo "== $service =="
  docker compose exec -T "$service" /opt/venv/bin/python - <<'PY'
import torch

print(f"torch={torch.__version__}")
print(f"cuda={torch.version.cuda}")
print(f"available={torch.cuda.is_available()}")
print(f"device_count={torch.cuda.device_count()}")
for index in range(torch.cuda.device_count()):
    print(f"device_{index}={torch.cuda.get_device_name(index)}")

device = torch.device("cuda:0")
for dtype in (torch.float32, torch.float16):
    a = torch.randn((1024, 1024), device=device, dtype=dtype)
    b = torch.randn((1024, 1024), device=device, dtype=dtype)
    c = a @ b
    torch.cuda.synchronize()
    print(f"matmul_{dtype}={float(c.float().mean().cpu()):.6f}")
PY
done
