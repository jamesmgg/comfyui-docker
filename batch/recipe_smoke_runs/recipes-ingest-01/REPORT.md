# Recipe smoke run recipes-ingest-01 (2026-06-10)

All flux2* and ltx23* reference workflows submitted unchanged (production settings)
via the ComfyUI API, one verified output each. Run spanned several runner
invocations (serial first, then parallel across both GPUs); elapsed times below
are per-recipe render times from submission to verified output.

| recipe | result | elapsed (s) | output |
| --- | --- | --- | --- |
| flux2-dev-fp8mixed | pass | ~490 (first model load) | outputs/gpu0/recipes-smoke/recipes-ingest-01/flux2-dev-fp8mixed_00001_.png |
| flux2-dev-turbo-lora | pass | 235.6 | outputs/gpu0/recipes-smoke/recipes-ingest-01/flux2-dev-turbo-lora_00001_.png |
| flux2-dev-q4km-gguf | pass | 225.6 | outputs/gpu0/recipes-smoke/recipes-ingest-01/flux2-dev-q4km-gguf_00001_.png |
| flux2-klein-base-4b-fp8 | pass (after fix) | 95.4 | outputs/gpu0/recipes-smoke/recipes-ingest-01/flux2-klein-base-4b-fp8_00001_.png |
| flux2-klein-9b-q6k-gguf | pass (after fix) | 105.2 | outputs/gpu0/recipes-smoke/recipes-ingest-01/flux2-klein-9b-q6k-gguf_00001_.png |
| ltx23-distilled-fp8 | pass (after fix) | 170.8 | outputs/gpu0/recipes-smoke/recipes-ingest-01/ltx23-distilled-fp8_00001_.mp4 |
| ltx23-distilled-dynamic-lora | pass (after fix) | 201.0 | outputs/gpu1/recipes-smoke/recipes-ingest-01/ltx23-distilled-dynamic-lora_00001_.mp4 |
| ltx23-dev-fp8 | pass (after fix) | 211.0 | outputs/gpu0/recipes-smoke/recipes-ingest-01/ltx23-dev-fp8_00001_.mp4 |
| ltx23-transition-lora | pass (after fix) | 210.9 | outputs/gpu1/recipes-smoke/recipes-ingest-01/ltx23-transition-lora_00001_.mp4 |

## Fixes applied during the run (validated against app/blueprints/)

1. **flux2-klein-base-4b-fp8 / flux2-klein-9b-q6k-gguf** — the reference workflows
   paired Klein with the Mistral FLUX.2 text encoder, which fails at the sampler
   with a 15360 vs 7680 conditioning shape mismatch. Per
   `app/blueprints/Image Edit (Flux.2 Klein 4B).json` and the bundled ComfyUI
   templates, Klein pairs with Qwen 3 encoders: 4B → `qwen_3_4b.safetensors`,
   9B → `qwen_3_8b_fp8mixed.safetensors` (+ `full_encoder_small_decoder.safetensors`
   VAE for 9B).
2. **all ltx23 recipes** — the reference workflows decoded with
   `VAELoader[full_encoder_small_decoder.safetensors]`, which is the FLUX.2 Dev
   blueprint's VAE; LTX latents fail in VAEDecodeTiled with a temporal shape
   mismatch (10 vs 128). Per `app/blueprints/Text to Video (LTX-2.3).json`, the
   VAE must come from `CheckpointLoaderSimple[ltx-2.3-22b-*.safetensors]`; the
   UNETLoader+VAELoader pair was replaced accordingly.

## Operational notes

- Submitting two ~18 GB flux2 model loads simultaneously restarted a worker
  (host RAM spike); the runner gained lost-prompt detection + one auto-resubmit,
  and heavy first loads are best staggered.
- Worker→output mapping: gpu0 = :8188 → outputs/gpu0, gpu1 = :8189 → outputs/gpu1.
