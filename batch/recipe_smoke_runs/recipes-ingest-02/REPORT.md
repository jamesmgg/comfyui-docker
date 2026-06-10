# Recipe smoke run recipes-ingest-02

| recipe | result | elapsed (s) | output |
| --- | --- | --- | --- |
| flux2-klein-base-4b-fp8 | pass | 100.6 | outputs/gpu0/recipes-smoke/recipes-ingest-02/flux2-klein-base-4b-fp8_00001_.png |
| ltx23-dev-fp8 | pass | 307.1 | outputs/gpu1/recipes-smoke/recipes-ingest-02/ltx23-dev-fp8_00001_.mp4 |
| ltx23-distilled-dynamic-lora | pass | 346.8 | outputs/gpu0/recipes-smoke/recipes-ingest-02/ltx23-distilled-dynamic-lora_00001_.mp4 |
| ltx23-distilled-fp8 | pass | 397.2 | outputs/gpu1/recipes-smoke/recipes-ingest-02/ltx23-distilled-fp8_00001_.mp4 |
| ltx23-transition-lora | pass | 211.4 | outputs/gpu0/recipes-smoke/recipes-ingest-02/ltx23-transition-lora_00001_.mp4 |

## Why this rerun (visual validation of run 01 found bad outputs)

Run 01 passed mechanically but visual inspection (user-confirmed in the CGM
gallery) showed five bad outputs:

- **flux2-klein-base-4b-fp8** — garbled badge text. The recipe used Flux.2 Dev
  wiring (ModelSamplingFlux + BasicScheduler + FluxGuidance + BasicGuider), but
  Klein base is not guidance-distilled. Rebuilt per
  `app/blueprints/Image Edit (Flux.2 Klein 4B).json` / bundled template:
  `Flux2Scheduler(20 steps)` + `CFGGuider(cfg=5)` with a real negative prompt.
- **all ltx23 recipes** — extreme red/yellow color blowout. The graphs paired
  CFG++ samplers (`euler_cfg_pp`) with `BasicGuider`; the blueprint pairs them
  with `CFGGuider(cfg=1)` fed by both LTXVConditioning outputs. Single-node fix
  confirmed by A/B test (`recipes-debug/cfgguider-test`), then applied to all 4.

All five rerun outputs verified visually frame-by-frame (correct color,
lighting, composition; minor sign-text spelling typical of video models).
Old broken registry variants/topologies archived in CGM; bad generations
rated down, verified ones rated up.
