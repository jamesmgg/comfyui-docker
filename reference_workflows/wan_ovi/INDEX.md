# Ovi (Wan 2.2 5B) — joint video + audio reference workflows

Ovi generates ~5s of video **with synchronized audio (speech + ambience)** in a
single sampling pass: one WanVideo model loader carries the video transformer
plus an `extra_model` audio transformer, and the sampler denoises video and
audio latents jointly. Verified end-to-end on 2026-06-10 (direct worker smoke on
gpu0 + first CGM-queued launch, job 1024 → generation 858967).

## Workflows

- `ovi-i2v-audio-704/workflow.json` — image-to-video+audio, 704×704, 121 frames
  @ 24fps (~5.04s), audio latent length 157, 50 steps / cfg 4 / shift 5 /
  unipc, EasyCache (thresh 0.015 from step 10), SLG block 11, block swap 15,
  `sdpa` attention, fp8-scaled quantization. Output: core `CreateVideo` +
  `SaveVideo` (h264 mp4 with muxed AAC) — **not** VHS_VideoCombine, so CGM's
  importer fast-path recognizes the output. Expects `example.png` (any image)
  in ComfyUI input storage; the LoadImage node is titled `image_1 — start
  frame` per the CGM multi-image convention.

This is the same graph registered in CGM: topology `1c34be8933cae8a0`, variant
`9d3e9e69c43f7e56`, label "Ovi I2V + Audio (704px, 5s)". Source of truth for
edits: `comfy-generation-manager/tools/vibebridge/ovi_i2v_audio.api.json`
(author changes through the vibecomfy-cgm-bridge skill, then re-push).

## Model inventory (all present)

| role | file | dir |
| --- | --- | --- |
| video transformer | `WanVideo/Ovi/Wan2_2_Ovi_Video_fp8_e4m3fn_scaled_KJ.safetensors` | `models/diffusion_models` |
| audio transformer (via `WanVideoExtraModelSelect` → `extra_model`) | `WanVideo/Ovi/Wan2_2_Ovi_Audio_fp8_e4m3fn_scaled_KJ.safetensors` | `models/diffusion_models` |
| video VAE | `Wan2_2_VAE_bf16.safetensors` | `models/vae` |
| text encoder | `umt5-xxl-enc-fp8_e4m3fn.safetensors` (Kijai, non-scaled) | `models/text_encoders` |
| audio VAE | `mmaudio_vae_16k_fp32.safetensors` | `models/mmaudio` |
| vocoder | `mmaudio_vocoder_bigvgan_best_netG_fp32.safetensors` | `models/mmaudio` |

## Prompt conventions (mandatory)

- Spoken words go inside `<S>...<E>` tags: `He says: <S>Hello there.<E>`.
  Without these tags the model still generates ambience but no speech.
- Optional audio description: `<AUDCAP>deep male voice, rain ambience<ENDAUDCAP>`.
- The single positive prompt drives BOTH models. Negative prompts can differ:
  the workflow has a second TextEncode node whose `negative_prompt`
  ("robotic, muffled, echo, distorted") feeds `WanVideoOviCFG` as the
  audio-side negative; `ovi_audio_cfg` 3.0 is the audio CFG scale.

## Audio conditioning

Ovi has **no driving-audio input** (no wav2vec lip-sync conditioning — that's
FantasyTalking/MultiTalk, different models). What the node set supports:

- Speech content/voice/ambience are steered by text (`<S>`/`<AUDCAP>` tags).
- `WanVideoEncodeOviAudio` (mmaudio_vae + AUDIO → `{"latent_ovi_audio": ...}`)
  encodes a reference audio clip into the same latent slot that
  `WanVideoEmptyMMAudioLatents` fills with zeros. Wired into the sampler's
  `samples` input (with reduced `denoise_strength`), this gives
  audio2audio-style init conditioning. All-zero latents are replaced by seeded
  noise inside the sampler; non-zero latents are used as-is as the init.
- `WanVideoAddOviAudioToLatents` merges audio latents into a video latent dict
  for combined video+audio inits (v2v+a2a continuation experiments).

## Gotchas (each one cost a debug cycle)

- `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (Comfy-Org scaled fp8) is
  **rejected** by WanVideoWrapper's T5 loader ("fp8 scaled is not supported");
  use Kijai's non-scaled `umt5-xxl-enc-fp8_e4m3fn.safetensors` with
  `quantization: fp8_e4m3fn`.
- `base_precision` must be `bf16` — fp16 produces black output (Kijai's note).
- Use `sdpa` attention; sage-attention was rolled back on these workers for
  bad WAN 2.2 output (see INVESTIGATION.md).
- `models/mmaudio` must be volume-mounted (compose has it since 47cc257);
  WanVideoWrapper registers the `mmaudio` folder only at import time.
- WanVideoWrapper/VideoHelperSuite import deps (`accelerate`, `cv2`,
  `imageio-ffmpeg`...) are baked into the image (Dockerfile custom-node deps
  layer). A missing `accelerate` silently kills ALL WanVideoWrapper nodes.
- Runtime: ~30 min per 5s clip on the 4090 (50 steps, EasyCache). fp8 weights
  fit fine in 24GB with 15-block swap.
