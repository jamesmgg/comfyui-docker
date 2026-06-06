# syntax=docker/dockerfile:1.7

FROM nvidia/cuda:13.0.0-cudnn-runtime-ubuntu24.04

ARG COMFYUI_TARBALL_URL=https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.tar.gz

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    COMFYUI_PATH=/workspace/ComfyUI

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

RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv "$VENV_PATH" \
    && "$VENV_PATH/bin/python" -m pip install --upgrade pip setuptools wheel

RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install \
        torch==2.10.0 \
        torchvision==0.25.0 \
        torchaudio==2.10.0 \
        --index-url https://download.pytorch.org/whl/cu130

RUN mkdir -p /tmp/comfyui-src /tmp/comfyui-reqs \
    && curl -L "$COMFYUI_TARBALL_URL" | tar -xz --strip-components=1 -C /tmp/comfyui-src \
    && cp /tmp/comfyui-src/requirements.txt /tmp/comfyui-reqs/requirements.txt \
    && cp /tmp/comfyui-src/manager_requirements.txt /tmp/comfyui-reqs/manager_requirements.txt \
    && rm -rf /tmp/comfyui-src

RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install -r /tmp/comfyui-reqs/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    "$VENV_PATH/bin/python" -m pip install -r /tmp/comfyui-reqs/manager_requirements.txt \
    && rm -rf /tmp/comfyui-reqs

COPY scripts/entrypoint.sh /usr/local/bin/comfyui-entrypoint
RUN chmod +x /usr/local/bin/comfyui-entrypoint

EXPOSE 8188

ENTRYPOINT ["comfyui-entrypoint"]
