#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 0 ]; then
  ports=("$@")
else
  ports=(8188 8189)
fi

for port in "${ports[@]}"; do
  echo "== localhost:$port =="
  curl -fsS "http://localhost:${port}/system_stats" > /dev/null
  curl -fsS "http://localhost:${port}/object_info" \
    | python3 -c 'import json,sys; data=json.load(sys.stdin); names=set(data); checks=["UNETLoader","VAELoader","CLIPLoader","Wan22ImageToVideoLatent","UNETLoaderMultiGPU","CLIPLoaderMultiGPU","DeviceSelectorMultiGPU"]; print("\n".join(f"{name}={name in names}" for name in checks)); missing=[name for name in checks if name not in names]; raise SystemExit(1 if missing else 0)'
done
