FROM ubuntu:24.04

ARG COMFYUI_TARBALL_URL=https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.tar.gz
ARG MULTIGPU_REPO=https://github.com/pollockjj/ComfyUI-MultiGPU.git
ARG MULTIGPU_COMMIT=b51c99a525e9607e43545ee2a8b7694c74a4775a
ARG GGUF_REPO=https://github.com/city96/ComfyUI-GGUF.git
ARG GGUF_COMMIT=main

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    COMFYUI_PATH=/workspace/ComfyUI \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64 \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        git \
        libgl1 \
        libglib2.0-0 \
        python3 \
        python3-pip \
        python3-venv \
        wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY constraints/pytorch-cu130.txt /tmp/pytorch-cu130.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv "$VENV_PATH" \
    && "$VENV_PATH/bin/python" -m pip install --upgrade pip setuptools wheel

RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install \
        -r /tmp/pytorch-cu130.txt \
        --index-url https://download.pytorch.org/whl/cu130

RUN mkdir -p "$COMFYUI_PATH" \
    && curl -L "$COMFYUI_TARBALL_URL" | tar -xz --strip-components=1 -C "$COMFYUI_PATH"

RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install \
        -c /tmp/pytorch-cu130.txt \
        -r "$COMFYUI_PATH/requirements.txt"

RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install \
        -c /tmp/pytorch-cu130.txt \
        -r "$COMFYUI_PATH/manager_requirements.txt"

# Triton-based attention kernel for --use-sage-attention (sm_80+; covers 3090/4090).
# Triton ships inside the cu130 torch wheel as pytorch-triton.
RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install \
        -c /tmp/pytorch-cu130.txt \
        sageattention==1.0.6 \
    && "$VENV_PATH/bin/python" -c "import sageattention"

RUN git clone "$MULTIGPU_REPO" "$COMFYUI_PATH/custom_nodes/ComfyUI-MultiGPU" \
    && git -C "$COMFYUI_PATH/custom_nodes/ComfyUI-MultiGPU" checkout "$MULTIGPU_COMMIT" \
    && rm -rf "$COMFYUI_PATH/custom_nodes/ComfyUI-MultiGPU/.git"

RUN git clone "$GGUF_REPO" "$COMFYUI_PATH/custom_nodes/ComfyUI-GGUF" \
    && git -C "$COMFYUI_PATH/custom_nodes/ComfyUI-GGUF" checkout "$GGUF_COMMIT" \
    && "$VENV_PATH/bin/python" -m pip install -c /tmp/pytorch-cu130.txt -r "$COMFYUI_PATH/custom_nodes/ComfyUI-GGUF/requirements.txt" \
    && rm -rf "$COMFYUI_PATH/custom_nodes/ComfyUI-GGUF/.git"

# Custom-node runtime dependencies (volume-mounted nodes; not baked in but their deps must be)
# WanVideoWrapper: accelerate/diffusers/peft needed at import time
# VideoHelperSuite: opencv (cv2) + imageio-ffmpeg needed at import time / video mux
RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install \
        -c /tmp/pytorch-cu130.txt \
        "accelerate>=1.2.1" \
        "diffusers>=0.33.0" \
        "peft>=0.17.0" \
        "ftfy" \
        "pyloudnorm" \
        "opencv-python-headless" \
        "imageio-ffmpeg"

COPY scripts/entrypoint.sh /usr/local/bin/comfyui-entrypoint
RUN chmod +x /usr/local/bin/comfyui-entrypoint

EXPOSE 8188 8189 8190

ENTRYPOINT ["comfyui-entrypoint"]
