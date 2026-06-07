#!/usr/bin/env python3
"""Run the Wan 2.2 T2V pilot and queue the 500 prompt batch."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "batch" / "wan22_t2v_manifest.json"
HIGHSTEP_MANIFEST = ROOT / "batch" / "wan22_t2v_highstep_manifest.json"
NEGATIVE = "text, logos, watermark, subtitles"
WORKERS = [
    {"port": 8188, "service": "comfyui-gpu0", "output_root": "outputs/gpu0", "weight": 54},
    {"port": 8189, "service": "comfyui-gpu1", "output_root": "outputs/gpu1", "weight": 46},
]


def api_prompt(item: dict, seed: int, highstep: bool = False) -> dict:
    if highstep:
        high_model = ["1", 0]
        low_model = ["2", 0]
        steps = 20
        split = 10
    else:
        high_model = ["7", 0]
        low_model = ["8", 0]
        steps = 4
        split = 2
    prompt = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"},
        },
        "2": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"},
        },
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"},
        },
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "5": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors",
                "strength_model": 1.0,
            },
        },
        "6": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["2", 0],
                "lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors",
                "strength_model": 1.0,
            },
        },
        "7": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["5", 0], "shift": 5.0}},
        "8": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["6", 0], "shift": 5.0}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": item["expanded_prompt"]}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": NEGATIVE}},
        "11": {
            "class_type": "EmptyHunyuanLatentVideo",
            "inputs": {"width": 640, "height": 640, "length": 81, "batch_size": 1},
        },
        "12": {
            "class_type": "KSamplerAdvanced",
            "inputs": {
                "model": high_model,
                "positive": ["9", 0],
                "negative": ["10", 0],
                "latent_image": ["11", 0],
                "add_noise": "enable",
                "noise_seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "start_at_step": 0,
                "end_at_step": split,
                "return_with_leftover_noise": "enable",
            },
        },
        "13": {
            "class_type": "KSamplerAdvanced",
            "inputs": {
                "model": low_model,
                "positive": ["9", 0],
                "negative": ["10", 0],
                "latent_image": ["12", 0],
                "add_noise": "disable",
                "noise_seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "start_at_step": split,
                "end_at_step": steps,
                "return_with_leftover_noise": "disable",
            },
        },
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["4", 0]}},
        "15": {
            "class_type": "SaveWEBM",
            "inputs": {
                "images": ["14", 0],
                "filename_prefix": item["filename_prefix"],
                "codec": "vp9",
                "fps": 16.0,
                "crf": 32.0,
            },
        },
    }
    if highstep:
        del prompt["5"]
        del prompt["6"]
        del prompt["7"]
        del prompt["8"]
    return prompt


def load_manifest(path: Path = MANIFEST) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(items: list[dict], path: Path = MANIFEST) -> None:
    path.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")


def build_highstep_manifest() -> list[dict]:
    source = load_manifest(MANIFEST)
    items: list[dict] = []
    for item in source:
        highstep_item = dict(item)
        highstep_item["status"] = "pending"
        highstep_item["assigned_port"] = None
        highstep_item["prompt_id"] = None
        highstep_item["output_subfolder"] = item["output_subfolder"].replace("wan-t2v-batch/", "wan-t2v-batch-highstep/")
        highstep_item["filename_prefix"] = item["filename_prefix"].replace("wan-t2v-batch/", "wan-t2v-batch-highstep/")
        highstep_item["output_file"] = None
        highstep_item["runtime_seconds"] = None
        highstep_item["verified"] = False
        items.append(highstep_item)
    return items


def post_json(port: int, path: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://localhost:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def submit(item: dict, port: int, highstep: bool = False) -> str:
    worker = find_worker(port)
    seed = 220000 + int(item["id"])
    if highstep:
        seed += 500000
    payload = {"prompt": api_prompt(item, seed, highstep=highstep), "client_id": str(uuid.uuid4())}
    response = post_json(port, "/prompt", payload)
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"missing prompt_id in response: {response}")
    item["status"] = "queued"
    item["assigned_port"] = port
    item["prompt_id"] = prompt_id
    item["runtime_seconds"] = None
    item["verified"] = False
    item["output_file"] = f"{worker['output_root']}/{item['filename_prefix']}_00001_.webm"
    return prompt_id


def wait_for_history(port: int, prompt_id: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        history = post_json(port, f"/history/{prompt_id}", None, timeout=15)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(5)
    raise TimeoutError(f"timed out waiting for prompt {prompt_id} on {port}")


def output_from_history(history: dict, worker: dict) -> str | None:
    outputs = history.get("outputs", {})
    for node in outputs.values():
        for video in node.get("videos", []):
            filename = video.get("filename")
            subfolder = video.get("subfolder", "")
            if filename:
                return str(Path(worker["output_root"]) / subfolder / filename)
    return None


def verify_video(path: str, worker: dict) -> None:
    container_path = "/workspace/ComfyUI/output/" + str(Path(path).relative_to(worker["output_root"]))
    result = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            worker["service"],
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=width,height,avg_frame_rate,nb_read_frames",
            "-of",
            "json",
            container_path,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    info = json.loads(result.stdout)
    stream = info["streams"][0]
    size = (ROOT / path).stat().st_size
    if stream.get("width") != 640 or stream.get("height") != 640:
        raise RuntimeError(f"unexpected dimensions: {stream}")
    if stream.get("avg_frame_rate") != "16/1":
        raise RuntimeError(f"unexpected frame rate: {stream}")
    if int(stream.get("nb_read_frames", 0)) != 81:
        raise RuntimeError(f"unexpected frame count: {stream}")
    if size < 100_000:
        raise RuntimeError(f"file too small: {size} bytes")


def find_worker(port: int) -> dict:
    return next(worker for worker in WORKERS if worker["port"] == port)


def run_pilot(args: argparse.Namespace) -> int:
    items = load_manifest()
    item = items[0]
    worker = find_worker(8188)
    started = time.time()
    prompt_id = submit(item, 8188)
    save_manifest(items)
    print(f"pilot queued {item['id']} on 8188: {prompt_id}", flush=True)
    history = wait_for_history(8188, prompt_id, args.timeout)
    item["runtime_seconds"] = round(time.time() - started, 3)
    item["status"] = "completed"
    item["output_file"] = output_from_history(history, worker)
    if not item["output_file"]:
        item["output_file"] = f"{worker['output_root']}/{item['filename_prefix']}_00001_.webm"
    verify_video(item["output_file"], worker)
    item["verified"] = True
    save_manifest(items)
    print(f"pilot verified {item['output_file']}", flush=True)
    return 0


def weighted_port(index: int) -> int:
    cycle = sum(worker["weight"] for worker in WORKERS)
    slot = index % cycle
    running = 0
    for worker in WORKERS:
        running += worker["weight"]
        if slot < running:
            return worker["port"]
    return WORKERS[-1]["port"]


def run_queue(args: argparse.Namespace) -> int:
    items = load_manifest()
    submitted = 0
    for index, item in enumerate(items[1:]):
        if item.get("prompt_id") and item.get("assigned_port"):
            continue
        port = weighted_port(index)
        try:
            prompt_id = submit(item, port)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"failed to queue {item['id']} on {port}: {detail}") from error
        submitted += 1
        if submitted % args.save_every == 0:
            save_manifest(items)
        print(f"queued {item['id']} on {port}: {prompt_id}", flush=True)
    save_manifest(items)
    print(f"submitted {submitted} prompts from 002-500", flush=True)
    return 0


def run_queue_highstep(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest) if args.manifest else HIGHSTEP_MANIFEST
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    if args.manifest:
        items = load_manifest(manifest_path)
    elif HIGHSTEP_MANIFEST.exists() and not args.rebuild:
        items = load_manifest(HIGHSTEP_MANIFEST)
    else:
        items = build_highstep_manifest()
        save_manifest(items, manifest_path)
    submitted = 0
    for index, item in enumerate(items):
        if item.get("prompt_id") and item.get("assigned_port"):
            continue
        port = weighted_port(index)
        try:
            prompt_id = submit(item, port, highstep=True)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"failed to queue highstep {item['id']} on {port}: {detail}") from error
        submitted += 1
        if submitted % args.save_every == 0:
            save_manifest(items, manifest_path)
        print(f"queued highstep {item['id']} on {port}: {prompt_id}", flush=True)
    save_manifest(items, manifest_path)
    print(f"submitted {submitted} highstep prompts from 001-500", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pilot = sub.add_parser("pilot")
    pilot.add_argument("--timeout", type=int, default=3600)
    queue = sub.add_parser("queue")
    queue.add_argument("--save-every", type=int, default=10)
    highstep = sub.add_parser("queue-highstep")
    highstep.add_argument("--save-every", type=int, default=10)
    highstep.add_argument("--rebuild", action="store_true")
    highstep.add_argument("--manifest")
    args = parser.parse_args()
    if args.command == "pilot":
        return run_pilot(args)
    if args.command == "queue":
        return run_queue(args)
    if args.command == "queue-highstep":
        return run_queue_highstep(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
