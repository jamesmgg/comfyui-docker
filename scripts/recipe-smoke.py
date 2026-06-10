#!/usr/bin/env python3
"""Run reference recipe workflows via the ComfyUI API and verify their outputs.

Submits each recipe's workflow.json unchanged except for filename_prefix
(a per-run key), keeping at most one prompt in flight per worker, then polls
/history until completion and asserts the declared output files exist with
nonzero size under the worker's outputs/ directory.

Usage:
  python3 scripts/recipe-smoke.py reference_workflows/non_wan_models/flux2-* \
      [--worker http://localhost:8188=outputs/gpu0] \
      [--worker http://localhost:8189=outputs/gpu1] \
      [--run-id 20260610-1200] [--timeout 1800]

Writes batch/recipe_smoke_runs/<run_id>/{REPORT.md,results.json}.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SAVE_CLASSES = {"SaveImage", "SaveVideo", "SaveWEBM", "SaveAudio", "SaveAudioMP3"}


def post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class Worker:
    def __init__(self, base_url: str, output_root: Path):
        self.base_url = base_url.rstrip("/")
        self.output_root = output_root
        self.current: dict | None = None  # active recipe state


def load_recipe(recipe_dir: Path, run_prefix: str) -> dict:
    workflow = json.loads((recipe_dir / "workflow.json").read_text())
    for node in workflow.values():
        if node.get("class_type") in SAVE_CLASSES:
            node["inputs"]["filename_prefix"] = f"{run_prefix}/{recipe_dir.name}"
    return workflow


def submit(worker: Worker, recipe_dir: Path, workflow: dict) -> dict:
    payload = {"prompt": workflow, "client_id": f"recipe-smoke-{uuid.uuid4()}"}
    try:
        response = post_json(f"{worker.base_url}/prompt", payload)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        return {"name": recipe_dir.name, "ok": False, "stage": "submit",
                "error": f"HTTP {error.code}: {detail[:2000]}"}
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        return {"name": recipe_dir.name, "ok": False, "stage": "submit",
                "error": f"no prompt_id in response: {response}"}
    return {"name": recipe_dir.name, "prompt_id": prompt_id,
            "worker": worker.base_url, "started": time.time()}


def check_history(worker: Worker, state: dict) -> dict | None:
    """Return a final result dict once the prompt finishes, else None."""
    history = get_json(f"{worker.base_url}/history/{state['prompt_id']}")
    entry = history.get(state["prompt_id"])
    if not entry:
        return None
    status = entry.get("status") or {}
    elapsed = round(time.time() - state["started"], 1)
    if status.get("status_str") == "error":
        messages = [m for m in status.get("messages", []) if m and m[0] == "execution_error"]
        return {"name": state["name"], "ok": False, "stage": "execution",
                "elapsed_s": elapsed, "error": json.dumps(messages)[:2000]}
    if not status.get("completed"):
        return None
    files: list[dict] = []
    for node_output in (entry.get("outputs") or {}).values():
        for kind in ("images", "video", "audio", "gifs"):
            for item in node_output.get(kind, []) or []:
                subfolder = item.get("subfolder") or ""
                path = worker.output_root / subfolder / item["filename"]
                files.append({
                    "path": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
                    "exists": path.is_file(),
                    "bytes": path.stat().st_size if path.is_file() else 0,
                })
    ok = bool(files) and all(f["exists"] and f["bytes"] > 0 for f in files)
    return {"name": state["name"], "ok": ok, "stage": "done" if ok else "verify",
            "elapsed_s": elapsed, "worker": worker.base_url, "files": files,
            **({} if ok else {"error": "no outputs declared" if not files else "output file missing/empty"})}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipes", nargs="+", help="recipe directories containing workflow.json")
    parser.add_argument("--worker", action="append", dest="workers", metavar="URL=OUTPUT_DIR",
                        help="worker base url and its output dir (repeatable)")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--timeout", type=int, default=1800, help="per-recipe timeout in seconds")
    args = parser.parse_args()

    worker_specs = args.workers or [
        "http://localhost:8188=outputs/gpu0",
        "http://localhost:8189=outputs/gpu1",
    ]
    workers = []
    for spec in worker_specs:
        url, _, output_dir = spec.partition("=")
        workers.append(Worker(url, (REPO_ROOT / output_dir).resolve()))

    recipe_dirs = []
    for raw in args.recipes:
        path = Path(raw)
        if not (path / "workflow.json").is_file():
            print(f"skip {raw}: no workflow.json", file=sys.stderr)
            continue
        recipe_dirs.append(path)
    if not recipe_dirs:
        print("no recipes to run", file=sys.stderr)
        return 2

    run_prefix = f"recipes-smoke/{args.run_id}"
    queue = list(recipe_dirs)
    results: list[dict] = []
    print(f"run {args.run_id}: {len(queue)} recipes across {len(workers)} workers")

    while queue or any(w.current for w in workers):
        for worker in workers:
            if worker.current is None and queue:
                recipe_dir = queue.pop(0)
                workflow = load_recipe(recipe_dir, run_prefix)
                state = submit(worker, recipe_dir, workflow)
                if state.get("ok") is False:
                    results.append(state)
                    print(f"  FAIL(submit) {state['name']}: {state['error'][:200]}")
                else:
                    worker.current = state
                    print(f"  queued {state['name']} on {worker.base_url} ({state['prompt_id']})")
        for worker in workers:
            if worker.current is None:
                continue
            state = worker.current
            try:
                final = check_history(worker, state)
            except (urllib.error.URLError, OSError) as error:
                print(f"  poll error for {state['name']}: {error}", file=sys.stderr)
                final = None
            if final is None and time.time() - state["started"] > args.timeout:
                final = {"name": state["name"], "ok": False, "stage": "timeout",
                         "elapsed_s": round(time.time() - state["started"], 1),
                         "error": f"no completion after {args.timeout}s"}
            if final is not None:
                results.append(final)
                worker.current = None
                print(f"  {'PASS' if final['ok'] else 'FAIL(' + final['stage'] + ')'} "
                      f"{final['name']} in {final.get('elapsed_s', '?')}s")
        time.sleep(5)

    run_dir = REPO_ROOT / "batch" / "recipe_smoke_runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    lines = [f"# Recipe smoke run {args.run_id}", "",
             "| recipe | result | elapsed (s) | output |", "| --- | --- | --- | --- |"]
    for result in sorted(results, key=lambda r: r["name"]):
        output = result.get("files", [{}])[0].get("path", "") if result.get("files") else ""
        verdict = "pass" if result["ok"] else f"FAIL ({result['stage']}): {result.get('error', '')[:120]}"
        lines.append(f"| {result['name']} | {verdict} | {result.get('elapsed_s', '')} | {output} |")
    (run_dir / "REPORT.md").write_text("\n".join(lines) + "\n")
    failed = [r for r in results if not r["ok"]]
    print(f"done: {len(results) - len(failed)}/{len(results)} passed; report at {run_dir / 'REPORT.md'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
