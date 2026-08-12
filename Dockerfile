# syntax=docker/dockerfile:1.7

ARG CUBE_BASE_IMAGE=ghcr.io/tencentcloud/cubesandbox-base:2026.16
FROM ${CUBE_BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_MAJOR=24
ARG CODEX_VERSION=0.147.0
ARG OPENCODE_VERSION=1.18.16

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       build-essential \
       ca-certificates \
       curl \
       file \
       git \
       git-lfs \
       gnupg \
       jq \
       less \
       openssh-client \
       procps \
       python3 \
       python3-pip \
       python3-venv \
       ripgrep \
       rsync \
       shellcheck \
       unzip \
       xz-utils \
       zip \
    && curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install --global \
       "@openai/codex@${CODEX_VERSION}" \
       "opencode-ai@${OPENCODE_VERSION}" \
    && git lfs install --system \
    && codex --version \
    && opencode --version \
    && node --version \
    && python3 --version \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm

ENV CODEX_HOME=/root/.codex \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    OPENCODE_DISABLE_AUTOUPDATE=true

RUN mkdir -p /workspace /root/.codex /root/.local/share/opencode

COPY scripts/smoke.sh /usr/local/bin/coding-agent-smoke

WORKDIR /workspace

# envd is inherited from cubesandbox-base and must remain the entrypoint.
EXPOSE 49983 4096 4500
