# syntax=docker/dockerfile:1.7

ARG CUBE_BASE_IMAGE=ghcr.io/tencentcloud/cubesandbox-base:2026.16
FROM ${CUBE_BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_MAJOR=24
ARG CODEX_VERSION=0.147.0
ARG OPENCODE_VERSION=1.18.16
ARG CLAUDE_CODE_VERSION=2.1.228
ARG DEEPSEEK_HARNESS_VERSION=0.1.0-rc.7

RUN sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g; s|http://security.ubuntu.com|https://security.ubuntu.com|g' /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get install -y --no-install-recommends \
       bash \
       build-essential \
       ca-certificates \
       curl \
       docker.io \
       file \
       git \
       git-lfs \
       gnupg \
       iproute2 \
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
       --allow-scripts=@anthropic-ai/claude-code,opencode-ai,@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs \
       "@openai/codex@${CODEX_VERSION}" \
       "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
       "@deepseek-ai/dsh@${DEEPSEEK_HARNESS_VERSION}" \
       "opencode-ai@${OPENCODE_VERSION}" \
    && git lfs install --system \
    && codex --version \
    && claude --version \
    && dsh --help >/dev/null \
    && docker --version \
    && dockerd --version \
    && opencode --version \
    && node --version \
    && python3 --version \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm

ENV CODEX_HOME=/root/.codex \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    OPENCODE_DISABLE_AUTOUPDATE=true

RUN useradd --create-home --shell /bin/bash agent \
    && mkdir -p /workspace /root/.codex /root/.local/share/opencode \
    && chown agent:agent /workspace

RUN cp /usr/local/bin/cube-entrypoint.sh /usr/local/bin/cube-entrypoint-base.sh

COPY docker/daemon.json /etc/docker/daemon.json
COPY scripts/cube-entrypoint.sh /usr/local/bin/cube-entrypoint.sh
COPY scripts/smoke.sh /usr/local/bin/coding-agent-smoke

RUN chmod 755 /usr/local/bin/cube-entrypoint.sh /usr/local/bin/coding-agent-smoke

WORKDIR /workspace

# envd is inherited from cubesandbox-base and must remain the entrypoint.
EXPOSE 49983 4096 4500
