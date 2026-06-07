# Non-Wan Smoke Run 20260606-184022

- Workflow source: `/mnt/c/users/jaime/documents/projects/comfyui-docker/reference_workflows/non_wan_models`
- Canonical reference input: `/mnt/c/users/jaime/documents/projects/comfyui-docker/inputs/reference_input.png`
- Queue policy: appended only; existing jobs were not cleared, interrupted, or reordered.

## Stage 1 Submitted

- `flux2-dev-fp8mixed` on port `8188` prompt `non-wan-smoke-20260606-184022-01`: accepted
- `qwen-image-fp8` on port `8188` prompt `non-wan-smoke-20260606-184022-02`: accepted
- `qwen-image-edit-2511-lightning-4step` on port `8188` prompt `non-wan-smoke-20260606-184022-03`: failed validation: missing Qwen Edit Lightning LoRA file
- `sam31-multiplex-segmentation` on port `8189` prompt `non-wan-smoke-20260606-184022-04`: failed validation: workflow saves a MASK directly with SaveImage
- `ltx23-distilled-fp8` on port `8189` prompt `non-wan-smoke-20260606-184022-05`: failed validation: LTX checkpoint/text encoder not exposed by current loader plus SaveVideo requires format/codec
- `stable-audio-3-medium-base` on port `8189` prompt `non-wan-smoke-20260606-184022-06`: accepted
- `sd15-v1-5-pruned` on port `8188` prompt `non-wan-smoke-20260606-184022-07`: accepted
- `anima-base-v1` on port `8189` prompt `non-wan-smoke-20260606-184022-08`: accepted

## Validation Failures

### qwen-image-edit-2511-lightning-4step

```json
{"error": {"type": "prompt_outputs_failed_validation", "message": "Prompt outputs failed validation", "details": "", "extra_info": {}}, "node_errors": {"20": {"errors": [{"type": "value_not_in_list", "message": "Value not in list", "details": "lora_name: 'Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors' not in ['Flux_2-Turbo-LoRA_comfyui.safetensors', 'QWEN_EDIT_ACTION_V1.safetensors', 'gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors', 'ltx2.3-transition.safetensors', 'ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors', 'wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors', 'wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors', 'wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors', 'wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors']", "extra_info": {"input_name": "lora_name", "input_config": [["Flux_2-Turbo-LoRA_comfyui.safetensors", "QWEN_EDIT_ACTION_V1.safetensors", "gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors", "ltx2.3-transition.safetensors", "ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors", "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors", "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors"], {}], "received_value": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"}}], "dependent_outputs": ["11"], "class_type": "LoraLoaderModelOnly"}}}
```

### sam31-multiplex-segmentation

```json
{"error": {"type": "prompt_outputs_failed_validation", "message": "Prompt outputs failed validation", "details": "Return type mismatch between linked nodes: images, received_type(MASK) mismatch input_type(IMAGE)", "extra_info": {}}, "node_errors": {"5": {"errors": [{"type": "return_type_mismatch", "message": "Return type mismatch between linked nodes", "details": "images, received_type(MASK) mismatch input_type(IMAGE)", "extra_info": {"input_name": "images", "input_config": ["IMAGE", {"tooltip": "The images to save."}], "received_type": "MASK", "linked_node": ["4", 0]}}], "dependent_outputs": ["5"], "class_type": "SaveImage"}}}
```

### ltx23-distilled-fp8

```json
{"error": {"type": "prompt_outputs_failed_validation", "message": "Prompt outputs failed validation", "details": "Required input is missing: format\nRequired input is missing: codec", "extra_info": {}}, "node_errors": {"1": {"errors": [{"type": "value_not_in_list", "message": "Value not in list", "details": "ckpt_name: 'ltx-2.3-22b-distilled-fp8.safetensors' not in ['hidream_o1_image_dev_fp8_scaled.safetensors', 'sam3.1_multiplex_fp16.safetensors', 'stable_audio_3_medium_base.safetensors', 'v1-5-pruned-emaonly-fp16.safetensors']", "extra_info": {"input_name": "ckpt_name", "input_config": [["hidream_o1_image_dev_fp8_scaled.safetensors", "sam3.1_multiplex_fp16.safetensors", "stable_audio_3_medium_base.safetensors", "v1-5-pruned-emaonly-fp16.safetensors"], {"tooltip": "The name of the checkpoint (model) to load."}], "received_value": "ltx-2.3-22b-distilled-fp8.safetensors"}}], "dependent_outputs": ["14"], "class_type": "CheckpointLoaderSimple"}, "2": {"errors": [{"type": "value_not_in_list", "message": "Value not in list", "details": "ckpt_name: 'ltx-2.3-22b-distilled-fp8.safetensors' not in ['hidream_o1_image_dev_fp8_scaled.safetensors', 'sam3.1_multiplex_fp16.safetensors', 'stable_audio_3_medium_base.safetensors', 'v1-5-pruned-emaonly-fp16.safetensors']", "extra_info": {"input_name": "ckpt_name", "input_config": ["COMBO", {"multiselect": false, "options": ["hidream_o1_image_dev_fp8_scaled.safetensors", "sam3.1_multiplex_fp16.safetensors", "stable_audio_3_medium_base.safetensors", "v1-5-pruned-emaonly-fp16.safetensors"]}], "received_value": "ltx-2.3-22b-distilled-fp8.safetensors"}}], "dependent_outputs": ["14"], "class_type": "LTXAVTextEncoderLoader"}, "14": {"errors": [{"type": "required_input_missing", "message": "Required input is missing", "details": "format", "extra_info": {"input_name": "format"}}, {"type": "required_input_missing", "message": "Required input is missing", "details": "codec", "extra_info": {"input_name": "codec"}}], "dependent_outputs": ["14"], "class_type": "SaveVideo"}}}
```

## Pending Stages

- Stage 2 remaining safetensors: `flux2-dev-turbo-lora`, `flux2-klein-base-4b-fp8`, `hidream-o1-image-dev`, `qwen-image-2512-fp8`, `qwen-image-2512-lightning-4step`, `qwen-360-diffusion-2512`, `qwen-illustration-1`, `qwen-image-edit-2511`
- Stage 3 Gemma/text-encoder probes: `ltx23-dev-fp8`, `ltx23-distilled-dynamic-lora`, `ltx23-transition-lora`
- Stage 4 GGUF after support install: `flux2-dev-q4km-gguf`, `flux2-klein-9b-q6k-gguf`

## GGUF Gate

ComfyUI-GGUF is not installed in `custom_nodes` at run creation time. Install and mount GGUF models only after active workers can be restarted safely, then verify `/object_info` exposes the GGUF loader classes before submitting Stage 4.
