# Planned: move `models/` to a Linux-native named volume

**Status: NOT applied (2026-06-10).** `docker-compose.yml` still uses the
original Windows-backed bind mounts; nothing in the repo references the
`comfy-models` volume yet. This doc is the full runbook for when we decide to
do it. **Run the benchmark gate first — do not start the 230 GB copy until the
benchmark passes.**

## Why

Model files are read through Docker Desktop's Windows file sharing at
**~130–165 MB/s** (measured 2026-06-10: timed 2 GiB `dd` reads of
`umt5-xxl-enc-fp8_e4m3fn.safetensors`). That makes model loading the dominant
fixed cost on every model switch and worker restart:

- Flux2 dev (34 GB): 3.5–5.5 min observed load on gpu1
- mistral_3_small_flux2_fp8 TE (17 GB): ~1.5–2 min
- Same fix-class as the CGM SQLite move to the `cgm-db` volume (virtiofs I/O
  storms; see CGM gallery-stall postmortem).

A named volume lives on ext4 inside the Docker Desktop VM disk (vhdx), which
typically reads at NVMe-class speeds (1–3 GB/s).

**Honest expectations:** this only shrinks the *disk-read* part of a load.
Dequant/cast, memory pinning, and host-to-GPU copies don't speed up. Realistic:
Flux2 34 GB load 3.5–5.5 min → ~1–1.5 min; Ovi-sized files (5–6 GB) → well
under 30 s. It does NOT help sampling speed, fp8 emulation on the 3090, or the
pinned-memory OOM restarts (separate fixes).

## Gate: benchmark before committing (~15 min, host PowerShell)

```powershell
# copy one 6.3 GB file into a scratch volume
docker run --rm -v "$PWD\models\text_encoders:/src:ro" `
  -v comfy-bench:/dst alpine cp /src/umt5-xxl-enc-fp8_e4m3fn.safetensors /dst/

# cold-read from the volume (drop VM page cache so it's a real disk read)
docker run --rm --privileged -v comfy-bench:/dst alpine sh -c `
  "sync && echo 3 > /proc/sys/vm/drop_caches; time cat /dst/umt5-xxl-enc-fp8_e4m3fn.safetensors > /dev/null"

# baseline: same read through the Windows mount
docker run --rm -v "$PWD\models\text_encoders:/src:ro" `
  alpine sh -c "time cat /src/umt5-xxl-enc-fp8_e4m3fn.safetensors > /dev/null"

docker volume rm comfy-bench   # cleanup
```

Decision rule: volume read **≥5× faster** → proceed. **<2×** → abandon (vhdx
drive too slow; the routing + pinned-memory fixes matter more anyway).

Other preflight: the volume lives in the Docker Desktop VM disk — need
**~240 GB free** on the drive holding the vhdx, on top of the existing copy
(storage is duplicated until staging is pruned).

## Migration runbook

Order matters: seed while workers keep running on the old binds; the compose
switch is the only step that touches live containers (pick an idle-queue
moment — `comfyui-gpu0`/`gpu1` are live, don't recreate casually).

1. Create `scripts/sync-models-volume.ps1` with the content in Appendix B.
2. Seed: `.\scripts\sync-models-volume.ps1` (~230 GB; rsync, resumable — re-run
   if interrupted).
3. Verify: `.\scripts\sync-models-volume.ps1 -Verify` (file counts + sizes must
   match between `.\models` and the volume).
4. Apply the compose change in Appendix A.
5. Switch: `docker compose up -d` (recreates both workers).
6. Validate: `curl http://localhost:8188/system_stats`, model lists populated
   via `/object_info`, then time a Flux2 or Ovi load against the numbers above.
7. Commit the compose + script changes.

### After the migration

- `.\models` on Windows becomes the **download/staging dir**: drop new model
  files there as usual, re-run `sync-models-volume.ps1`, workers pick them up
  without a restart.
- Deleting from `.\models` does NOT delete from the volume (rsync runs without
  `--delete`), so staging can be pruned to reclaim space. To delete from the
  volume: `docker run --rm -v comfy-models:/m alpine rm /m/<subdir>/<file>`.
- `outputs/`, `inputs/`, `custom_nodes/`, `user/` deliberately stay on Windows
  binds — CGM reads worker outputs through those paths.
- The volume survives rebuilds/recreates; only `docker volume rm comfy-models`
  destroys it.

### Rollback

`git checkout -- docker-compose.yml && docker compose up -d` — the full model
set still exists at `.\models`, so reverting the mounts restores the old setup.
The volume can be kept or `docker volume rm`'d.

## Appendix A — compose change

In **all three services** (gpu0, gpu1, sharded), replace the 17
`./models/<subdir>:...` bind lines with a single mount:

```yaml
      - comfy-models:/workspace/ComfyUI/models
```

and add at the bottom of the file:

```yaml
volumes:
  # external: compose must never auto-create this empty — seed it first with
  # scripts/sync-models-volume.ps1.
  comfy-models:
    external: true
```

`external: true` is deliberate: if the volume hasn't been seeded, compose fails
loudly instead of silently starting workers with an empty models dir.

## Appendix B — `scripts/sync-models-volume.ps1`

```powershell
# Seed/sync the `comfy-models` Docker named volume from .\models (Windows staging dir).
# Incremental + resumable; re-run any time new models are downloaded.
param([switch]$Verify)

$src = Join-Path $PSScriptRoot "..\models" | Resolve-Path

if ($Verify) {
    Write-Host "--- staging (.\models) ---"
    docker run --rm -v "${src}:/src:ro" alpine sh -c "du -sh /src && find /src -type f | wc -l"
    Write-Host "--- volume (comfy-models) ---"
    docker run --rm -v comfy-models:/dst alpine sh -c "du -sh /dst && find /dst -type f | wc -l"
    exit
}

docker run --rm `
    -v "${src}:/src:ro" `
    -v comfy-models:/dst `
    alpine sh -c "apk add --no-cache rsync >/dev/null && rsync -rt --info=progress2 /src/ /dst/"
```
