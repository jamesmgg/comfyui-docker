#!/usr/bin/env python3
"""Extract embedded ComfyUI metadata from generated WebM outputs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "batch" / "output_metadata_index.json"
WORKERS = {
    "gpu0": {"service": "comfyui-gpu0", "output_root": "outputs/gpu0"},
    "gpu1": {"service": "comfyui-gpu1", "output_root": "outputs/gpu1"},
}


CONTAINER_EXTRACTOR = r"""
import json
import os
import subprocess

root = "/workspace/ComfyUI/output"
worker = os.environ["METADATA_WORKER"]
output_root = os.environ["METADATA_OUTPUT_ROOT"]
records = []


def workflow_nodes(workflow, class_type):
    if not isinstance(workflow, dict):
        return []
    return [
        {"id": node_id, **node}
        for node_id, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") == class_type
    ]


def model_loader_nodes(workflow):
    if not isinstance(workflow, dict):
        return []
    nodes = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type", "")
        if "Loader" in class_type or class_type in ("LoraLoaderModelOnly", "ModelSamplingSD3"):
            nodes.append(
                {
                    "id": node_id,
                    "class_type": class_type,
                    "inputs": node.get("inputs", {}),
                }
            )
    return nodes


for dirpath, _, filenames in os.walk(root):
    for filename in sorted(name for name in filenames if name.lower().endswith(".webm")):
        path = os.path.join(dirpath, filename)
        rel = os.path.relpath(path, root).replace("\\", "/")
        output_file = f"{output_root}/{rel}"
        try:
            raw_probe = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    path,
                ],
                text=True,
            )
            probe = json.loads(raw_probe)
        except Exception as exc:
            records.append({"worker": worker, "output_file": output_file, "error": str(exc)})
            continue

        fmt = probe.get("format") or {}
        tags = fmt.get("tags") or {}
        prompt_tag = tags.get("PROMPT") or tags.get("prompt")
        workflow = None
        if prompt_tag:
            try:
                workflow = json.loads(prompt_tag)
            except Exception:
                workflow = prompt_tag

        text_nodes = workflow_nodes(workflow, "CLIPTextEncode")
        samplers = workflow_nodes(workflow, "KSamplerAdvanced") + workflow_nodes(workflow, "KSampler")
        save_webm = workflow_nodes(workflow, "SaveWEBM")

        records.append(
            {
                "worker": worker,
                "output_file": output_file,
                "duration": fmt.get("duration"),
                "size": fmt.get("size"),
                "format_tags": {key: value for key, value in tags.items() if key.upper() != "PROMPT"},
                "positive_prompt": text_nodes[0].get("inputs", {}).get("text") if len(text_nodes) > 0 else None,
                "negative_prompt": text_nodes[1].get("inputs", {}).get("text") if len(text_nodes) > 1 else None,
                "samplers": [
                    {
                        "id": node["id"],
                        "class_type": node.get("class_type"),
                        "inputs": node.get("inputs", {}),
                    }
                    for node in samplers
                ],
                "save_webm": [
                    {"id": node["id"], "inputs": node.get("inputs", {})}
                    for node in save_webm
                ],
                "model_loaders": model_loader_nodes(workflow),
                "api_workflow": workflow,
            }
        )

print(json.dumps(records, ensure_ascii=False))
"""


def load_manifest_records() -> dict[str, dict]:
    records: dict[str, dict] = {}
    for path in sorted((ROOT / "batch").glob("*manifest.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data:
            output_file = row.get("output_file")
            if output_file:
                records[output_file] = {"manifest": str(path.relative_to(ROOT)), **row}
    return records


def extract_worker(worker: str) -> list[dict]:
    config = WORKERS[worker]
    env = {
        "METADATA_WORKER": worker,
        "METADATA_OUTPUT_ROOT": config["output_root"],
    }
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "-e",
        f"METADATA_WORKER={env['METADATA_WORKER']}",
        "-e",
        f"METADATA_OUTPUT_ROOT={env['METADATA_OUTPUT_ROOT']}",
        config["service"],
        "python3",
        "-c",
        CONTAINER_EXTRACTOR,
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout[-4000:] or "no stderr/stdout captured"
        raise RuntimeError(
            f"metadata extraction failed for {worker} ({config['service']}):\n{details}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        tail = result.stdout[-4000:]
        raise RuntimeError(
            f"metadata extraction returned invalid JSON for {worker} ({config['service']}): {exc}\n{tail}"
        ) from exc


def build_index(workers: list[str], include_manifests: bool) -> list[dict]:
    records: list[dict] = []
    for worker in workers:
        records.extend(extract_worker(worker))

    manifest_by_output = load_manifest_records() if include_manifests else {}
    for record in records:
        record["manifest_record"] = manifest_by_output.get(record.get("output_file"))
    return sorted(records, key=lambda row: row.get("output_file", ""))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--worker",
        action="append",
        choices=sorted(WORKERS),
        help="Worker to extract. Repeat for multiple workers. Defaults to both workers.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path. Defaults to {DEFAULT_OUTPUT.relative_to(ROOT)}.",
    )
    parser.add_argument(
        "--no-manifests",
        action="store_true",
        help="Do not merge matching records from batch/*manifest.json.",
    )
    parser.add_argument("--compact", action="store_true", help="Write compact JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workers = args.worker or sorted(WORKERS)
    records = build_index(workers, include_manifests=not args.no_manifests)

    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.compact:
        output.write_text(json.dumps(records, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        output.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    embedded = sum(1 for record in records if isinstance(record.get("api_workflow"), dict))
    manifested = sum(1 for record in records if record.get("manifest_record"))
    print(f"wrote {output}")
    print(f"records: {len(records)}")
    print(f"with embedded workflow: {embedded}")
    print(f"with manifest match: {manifested}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
