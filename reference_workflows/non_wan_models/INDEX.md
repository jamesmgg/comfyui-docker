# Non-Wan model smoke-test reference workflows

Each subdirectory contains a ComfyUI API `workflow.json` intended as a starting point for `/prompt` smoke tests. These are reference workflows, not generated output history.

Source templates used:

- `custom_nodes/ComfyUI-MultiGPU/ci/example_workflows_api/*` for API prompt topology.
- `app/blueprints/*` for current ComfyUI model-family loader classes and default model filenames.

Input-free workflows:

- `qwen-image-fp8`
- `qwen-image-2512-fp8`
- `qwen-image-2512-lightning-4step`
- `qwen-360-diffusion-2512`
- `qwen-illustration-1`
- `anima-base-v1`
- `sd15-v1-5-pruned`
- `flux2-dev-fp8mixed`
- `flux2-dev-turbo-lora`
- `flux2-klein-base-4b-fp8`
- `flux2-dev-q4km-gguf`
- `flux2-klein-9b-q6k-gguf`
- `stable-audio-3-medium-base`
- `ltx23-dev-fp8`
- `ltx23-distilled-fp8`
- `ltx23-distilled-dynamic-lora`
- `ltx23-transition-lora`
- `hidream-o1-image-dev`

Input-dependent workflows:

- `qwen-image-edit-2511` expects `reference_input.png` in ComfyUI input storage.
- `qwen-image-edit-2511-lightning-4step` expects `reference_input.png` in ComfyUI input storage.
- `sam31-multiplex-segmentation` expects `reference_input.png` in ComfyUI input storage.

Notes:

- Qwen and FLUX.2 lightning/turbo references use `LoraLoaderModelOnly` because the bundled blueprints model those accelerators as model-only LoRAs.
- LTX 2.3 spatial upscaler is not a standalone smoke-test graph here; it is a latent upscale model used as a second-stage component after a base LTX generation.
- GGUF FLUX.2 *dev* references use the local safetensors Mistral FLUX.2 text encoder because the GGUF text-encoder companion files from the MultiGPU examples were not present in the model inventory.
- FLUX.2 Klein models pair with Qwen 3 text encoders, not Mistral (per the bundled ComfyUI templates): Klein 4B → `qwen_3_4b.safetensors`, Klein 9B → `qwen_3_8b_fp8mixed.safetensors` + `full_encoder_small_decoder.safetensors` VAE. Using the Mistral encoder fails at the sampler with a 15360→7680 conditioning shape mismatch.
