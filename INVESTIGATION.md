# Worker health investigation runbook (RTX 4090 + RTX 3090)

**Audience:** an LLM/operator with shell + Docker access **on the Windows host**
(or its WSL/Docker Desktop daemon) that actually runs the ComfyUI containers.
**Goal:** confirm both ComfyUI workers are healthy and producing correct WAN
output after the SageAttention optimization was rolled back, and decide whether
the remaining `--fast` flags are safe.

## Topology (memorize this — it's easy to invert)

| Container       | GPU       | Arch / sm | Host port | API base                  |
|-----------------|-----------|-----------|-----------|---------------------------|
| `comfyui-gpu0`  | RTX 4090  | Ada sm_89 | 8188      | `http://localhost:8188`   |
| `comfyui-gpu1`  | RTX 3090  | Amp sm_86 | 8189      | `http://localhost:8189`   |
| `comfyui-sharded` (optional, profile `sharded`) | both | — | 8190 | `http://localhost:8190` |

Repo: `comfyui-docker/`. Live config is in `docker-compose.yml`. Run all
`docker compose` commands from that directory.

## What changed and why we're investigating

- SageAttention (`--use-sage-attention`) was added, then **rolled back** because
  it produced bad WAN 2.2 output. Confirm it is gone from both workers (step 2).
- Still live and quality-affecting:
  - `comfyui-gpu0` (4090): `--fast fp16_accumulation fp8_matrix_mult`
  - `comfyui-gpu1` (3090): `--fast fp16_accumulation`
- **Primary suspect if WAN issues persist:** `fp8_matrix_mult` on the 4090. It
  routes fp8_scaled matmuls through the 4090's FP8 tensor cores and can shift or
  degrade output on fp8 models like WAN 2.2 14B. `fp16_accumulation` is far
  lower-risk but is still a candidate. The 3090 has no FP8 hardware, so any WAN
  difference that appears **only on the 4090** points straight at `fp8_matrix_mult`.

## ⚠️ Critical environment caveat — read before trusting any `docker` command

There are potentially **two Docker daemons**: the Windows host's Docker Desktop
(which runs the live workers) and any sandbox/inner daemon. `docker logs` and
`docker ps` only show containers on the daemon you're talking to.

**First action — confirm you can see the real containers:**

```bash
docker ps --filter name=comfyui --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
```

- If this lists `comfyui-gpu0` and `comfyui-gpu1` with port mappings → you are on
  the right daemon; logs and `compose exec` will work. Proceed.
- If it is **empty** but `curl http://localhost:8188/system_stats` succeeds → you
  are on the wrong daemon (you can reach the workers over HTTP but cannot read
  their logs or exec into them). Switch to the host Docker context
  (`docker context ls` / `docker context use desktop-linux`) or run from a host
  shell before continuing. Steps that need logs/exec are marked **[needs host
  daemon]**.

Do **not** `docker compose up/down/restart/stop` these workers — they serve live
generation jobs and a restart kills in-flight WAN prompts. Read-only inspection,
`exec`, and submitting smoke prompts over HTTP are all fine.

---

## Step 1 — Reachability and identity (HTTP only, works from anywhere)

```bash
for p in 8188 8189; do
  echo "== :$p =="
  curl -fsS --max-time 5 "http://localhost:$p/system_stats" \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);s=d["system"];g=d["devices"][0];print("argv:"," ".join(s["argv"]));print("torch:",s["pytorch_version"]);print("device:",g["name"]);print("vram_free_GB: %.1f"%(g["vram_free"]/1e9))'
done
```

Healthy result:
- `:8188` device contains **RTX 4090**; `:8189` device contains **RTX 3090**.
  (If these are swapped, the GPU-to-port mapping is wrong — stop and flag it.)
- `torch: 2.10.0+cu130` on both.
- Device name ends in `cudaMallocAsync` (async allocator active).

## Step 2 — Confirm SageAttention is gone and flags are as expected

From the argv printed above:
- **Neither** worker should contain `--use-sage-attention`. If one still does,
  that worker is running the bad config — it needs a recreate at the next safe
  window (don't restart unprompted; report it).
- `:8188` argv should contain `--fast fp16_accumulation fp8_matrix_mult`.
- `:8189` argv should contain `--fast fp16_accumulation` (and **not**
  `fp8_matrix_mult`).
- Cross-check against `docker-compose.yml`. **[needs host daemon]** Running argv
  can drift from compose if a container wasn't recreated after an edit — the
  source of truth for "what's running" is `system_stats`, not the file.

## Step 3 — Logs: scan for load-time and runtime errors **[needs host daemon]**

```bash
# Startup banner: which device, attention backend, any import failures
docker logs comfyui-gpu0 2>&1 | head -80
docker logs comfyui-gpu1 2>&1 | head -80

# Recent activity + errors across the last run window
docker logs --since 2h comfyui-gpu0 2>&1 | grep -iE 'error|traceback|out of memory|oom|cuda|nan|fail|assert|fallback|warn' | tail -60
docker logs --since 2h comfyui-gpu1 2>&1 | grep -iE 'error|traceback|out of memory|oom|cuda|nan|fail|assert|fallback|warn' | tail -60
```

Look for:
- `Using sage attention` / `Using sub quadratic` / `Using pytorch attention` —
  confirms which attention backend each worker actually loaded. Should be the
  default PyTorch path now, **not** sage.
- `fp8` / `fp8_matrix_mult` mentions during model load on the 4090.
- `CUDA out of memory`, `NaN`, `inf`, repeated `Prompt executed` failures,
  `got prompt` with no matching completion, or tracebacks at sampling time.
- A worker that logs `got prompt` but never `Prompt executed` is **wedged** —
  the most likely real failure mode. Cross-check with the queue (step 6).

## Step 4 — Compute sanity (CUDA matmul) **[needs host daemon]**

```bash
cd comfyui-docker
scripts/cuda-smoke.sh                 # both workers; or: scripts/cuda-smoke.sh comfyui-gpu0
```

Healthy: each worker prints `available=True`, the correct `device_0=...` name,
and finite `matmul_torch.float32` / `matmul_torch.float16` means (a number, not
`nan`/`inf`). A `nan` here would indicate a deeper numerical problem.

## Step 5 — API + node registration (HTTP only)

```bash
cd comfyui-docker
scripts/api-smoke.sh                  # both ports; checks UNETLoader/VAELoader/CLIPLoader/Wan22ImageToVideoLatent/MultiGPU nodes
```

Healthy: every checked node prints `=True` and the script exits 0. A missing
WAN/MultiGPU node means the custom-node load failed (check step 3 logs).

## Step 6 — Live queue / GPU utilization (is each card actually working?)

HTTP queue depth per worker:
```bash
for p in 8188 8189; do echo "== :$p =="; curl -fsS "http://localhost:$p/queue" \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print("running:",len(d.get("queue_running",[])),"pending:",len(d.get("queue_pending",[])))'; done
```

GPU-side utilization **[needs host daemon, host has nvidia-smi]**:
```bash
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv
```
When a worker is mid-job its GPU should show high `utilization.gpu` and several
GB `memory.used`. A worker that claims a `running` prompt but whose GPU sits at
~0% util is wedged (kill/recreate at a safe window).

## Step 7 — Functional WAN smoke (the real correctness test)

This submits a tiny real WAN 2.2 prompt to both workers concurrently and writes
to `outputs/gpu0` and `outputs/gpu1` (does **not** touch the comfy-generation-
manager SQLite queue):

```bash
cd comfyui-docker
python3 scripts/wan-parallel-smoke.py            # both; prints queued prompt_ids
```

Then confirm completion and inspect the output:
```bash
# poll history for each queued prompt_id
curl -fsS "http://localhost:8188/history/<PROMPT_ID>" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(json.dumps(d,indent=2)[:1200])'
# newest files written by each worker
ls -lt outputs/gpu0 | head; ls -lt outputs/gpu1 | head
```
Healthy: both prompts reach `status: success` in `/history`, a new video file
appears under each `outputs/gpuN`, and it plays without corruption. A prompt that
errors returns a node traceback in the history payload — capture it verbatim.

## Step 8 — A/B test to isolate the remaining suspect flag (do this if WAN output still looks wrong)

The point: prove whether `fp8_matrix_mult` (4090-only) is degrading WAN. The
3090 is the built-in control — it never had that flag.

1. Generate the **same** WAN prompt+seed on the 4090 (`:8188`) and the 3090
   (`:8189`). Use a real production-style workflow, not just the tiny smoke, so
   artifacts are visible. Keep seed, resolution, steps, sampler identical.
2. Compare outputs:
   - If the 3090 looks correct and the 4090 looks degraded → `fp8_matrix_mult`
     is the cause. Recommended fix: change `comfyui-gpu0`'s `COMFYUI_ARGS` in
     `docker-compose.yml` to `--fast fp16_accumulation` (drop `fp8_matrix_mult`),
     and recreate **only that worker at a safe window**:
     `docker compose up -d --force-recreate --no-deps comfyui-gpu0`.
   - If **both** look degraded vs a known-good baseline → suspect
     `fp16_accumulation`. Test by removing `--fast` entirely from one worker and
     re-running the same prompt+seed.
   - If both look correct → the `--fast` flags are safe; the SageAttention
     rollback already resolved the WAN issue and no further change is needed.
3. Keep a known-good reference output from **before** any `--fast` flags (plain
   `--reserve-vram 1.0 --preview-method none`) as the baseline for "correct."

To A/B without disturbing live workers, you can launch a throwaway worker on a
spare port from the same image with custom args, e.g.:
```bash
docker compose run --rm -p 8191:8191 -e COMFYUI_ARGS="--listen 0.0.0.0 --port 8191 --reserve-vram 1.0 --preview-method none --enable-manager --enable-assets --input-directory /workspace/ComfyUI/input --output-directory /workspace/ComfyUI/output --temp-directory /workspace/ComfyUI/temp --user-directory /workspace/ComfyUI/user" comfyui-gpu0
```
(That command pins to GPU0/the 4090 via the service's device request; it runs a
plain-args 4090 worker on :8191 for a clean baseline without recreating the live
one. Stop it with Ctrl-C when done.)

## Step 9 — Cross-check via comfy-generation-manager (optional, end-to-end)

CGM (`http://localhost:8765`) is the durable queue/dispatcher in front of both
workers. Its health endpoint summarizes worker reachability and importer state:
```bash
curl -fsS http://localhost:8765/api/health | python3 -m json.tool
```
- `workers[]` should show both reachable.
- Recent `lost` attempts in the jobs data indicate a worker dropped in-flight
  prompts (restart/wedge) — corroborates a step-3/step-6 finding.
- Do **not** launch workflow smoke tests through CGM against the live DB unless
  real pending jobs are intended.

## Reporting template

Report back, per worker:
- Reachable? correct GPU on correct port? torch version?
- Exact live argv; SageAttention absent? which `--fast` flags?
- Log scan: any errors/OOM/NaN/wedged (`got prompt` w/o `Prompt executed`)?
- `cuda-smoke` finite? `api-smoke` all nodes present?
- WAN smoke: both succeeded? output files valid?
- If quality still wrong: A/B verdict — which flag, on which GPU, with the two
  sample outputs attached.
- Recommended action (and explicitly: whether a recreate is needed, and that it
  must wait for a safe window because the workers serve live jobs).
