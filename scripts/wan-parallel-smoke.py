#!/usr/bin/env python3
"""Submit a tiny Wan 2.2 smoke prompt to two ComfyUI workers.

This is an API-format smoke harness, not a quality preset. It intentionally uses
the Wan filenames tracked under models/ and keeps dimensions/steps small enough
for quick validation.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
import uuid


def build_prompt(port: int) -> dict:
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
                "weight_dtype": "default",
            },
        },
        "2": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
                "weight_dtype": "default",
            },
        },
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "wan",
                "device": "default",
            },
        },
        "4": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "wan_2.1_vae.safetensors"},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["3", 0],
                "text": "a small ceramic teapot on a wooden table",
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["3", 0],
                "text": "blurry, low quality, distorted",
            },
        },
        "7": {
            "class_type": "Wan22ImageToVideoLatent",
            "inputs": {
                "vae": ["4", 0],
                "width": 320,
                "height": 192,
                "length": 5,
                "batch_size": 1,
            },
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
                "seed": 1000 + port,
                "steps": 4,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["8", 0],
                "vae": ["4", 0],
            },
        },
        "10": {
            "class_type": "SaveWEBM",
            "inputs": {
                "images": ["9", 0],
                "filename_prefix": f"wan-smoke/worker-{port}",
                "codec": "vp9",
                "fps": 8.0,
                "crf": 40.0,
            },
        },
    }


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def submit(port: int) -> None:
    client_id = str(uuid.uuid4())
    payload = {"prompt": build_prompt(port), "client_id": client_id}
    response = post_json(f"http://localhost:{port}/prompt", payload)
    print(f"{port}: queued {response.get('prompt_id')}")


def main() -> int:
    ports = [int(arg) for arg in sys.argv[1:]] or [8188, 8189]
    threads = [threading.Thread(target=submit, args=(port,)) for port in ports]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
