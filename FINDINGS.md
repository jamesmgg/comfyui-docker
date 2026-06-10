# Deep analysis — dual-GPU runtime (RTX 4090 + RTX 3090)

Audit date: 2026-06-10. Verified against the live workers via `/system_stats`:
GPU0 worker (port 8188) = **RTX 4090**, GPU1 worker (port 8189) = **RTX 3090**,
both on ComfyUI 0.24.0, PyTorch 2.10.0+cu130, Python 3.12, cudaMallocAsync
active, 64 GB host RAM. Primary workload: Wan 2.2 14B fp8 video.

## Addressed in this commit

### 1. Per-GPU `--fast` flags (previously identical args on both workers)
The 4090 (Ada, sm_89) has FP8 tensor cores; the fp8_scaled Wan models were
being dequantized to fp16 for every matmul. The 3090 (Ampere, sm_86) has no
FP8 hardware.

- GPU0 (4090): `--fast fp16_accumulation fp8_matrix_mult`
- GPU1 (3090): `--fast fp16_accumulation`
- Sharded worker: `--fast fp16_accumulation` only, since its ops can land on
  either GPU.

These are ComfyUI "untested" performance features and can affect output
quality. Roll back per-worker by removing the flag from that worker's
`COMFYUI_ARGS`. After the next container recreate, compare a sample
generation per worker against a pre-change output before trusting batches.

### 2. SageAttention (previously plain PyTorch SDPA)
`sageattention==1.0.6` (Triton kernels, sm_80+, so both cards) is now baked
into the image and both workers pass `--use-sage-attention`. This is
typically the largest single speedup for attention-heavy video models like
Wan. Same rollback rule: remove the flag from `COMFYUI_ARGS` if quality
shifts.

### 3. Torch pin enforcement in pip installs
`pip install -r requirements.txt` (ComfyUI, manager, GGUF) previously ran
without the cu130 constraint file, so any dependency could silently replace
the pinned `torch==2.10.0+cu130` with a PyPI CPU wheel. All pip installs in
the Dockerfile now pass `-c /tmp/pytorch-cu130.txt`.

### 4. Healthchecks
All three services now have a `curl /system_stats` healthcheck (30s interval,
120s start period). Note: plain Docker does **not** restart unhealthy
containers — `restart: unless-stopped` only fires on exit. The healthcheck
surfaces wedged workers in `docker ps` / compose status; auto-restart would
need an autoheal sidecar (deferred below).

### 5. Container drift observed
At audit time the live GPU1 container was running without `--enable-assets`
even though docker-compose.yml includes it — containers had not been
recreated after a compose edit. None of this commit's changes apply until
the containers are recreated (`docker compose up -d --build`), which was
deliberately not done because the workers were busy.

## Known-good (no change needed)

- GPU pinning via Docker device requests + `CUDA_VISIBLE_DEVICES`, with
  single-GPU workers intentionally omitting `--cuda-device`/`--default-device`
  (ComfyUI rewrites `CUDA_VISIBLE_DEVICES` from those flags).
- `--reserve-vram 1.0` is appropriate on 24 GB cards.
- `--preview-method none` avoids preview overhead on headless workers.
- cudaMallocAsync auto-enabled; pinned memory on by default.
- Sharded profile correctly isolated behind `--profile sharded`.

## Deferred / follow-ups

1. **Recreate + benchmark.** After the current batch drains:
   `docker compose up -d --build`, then `scripts/cuda-smoke.sh`,
   `scripts/api-smoke.sh`, `python3 scripts/wan-parallel-smoke.py`. Compare
   per-step it/s in worker logs before/after, and A/B one output per worker
   for quality.
2. **Pin the ComfyUI tarball and GGUF commit.** The image builds from
   `master.tar.gz` and `GGUF_COMMIT=main`, so image contents depend on build
   date and layer-cache state. Pin `COMFYUI_TARBALL_URL` to a release tag
   (v0.24.0 matches the running workers) and GGUF to a SHA.
3. **Rebalance `scripts/wan22-t2v-batch.py` weights.** Current 54/46
   (GPU0/GPU1) undersells the 4090, which is roughly 1.5–1.9× a 3090 on
   diffusion. ~62/38 is a better starting point; tune from measured batch
   throughput. Keep both GPUs busy — never serialize.
4. **Measure model-load I/O.** `models/` (403 GB) is a Windows-backed bind
   mount; cold loads of the ~14 GB Wan fp8 files cross Docker Desktop's file
   sharing layer. The 64 GB page cache hides repeat loads. If cold loads or
   model switches are slow, move models to a WSL-native disk or named volume.
5. **Optional autoheal.** If wedged-worker auto-restart is wanted, add an
   autoheal container keyed on the new healthchecks.
6. **Optional NVENC.** `NVIDIA_DRIVER_CAPABILITIES=compute,utility` omits
   `video`; add it only if ffmpeg NVENC encoding inside the containers is
   ever needed (current VP9/WebM encodes are CPU anyway).
