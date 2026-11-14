# hub-tools: ferramentas de operação sem instalar nada no host.
# sops (binário oficial, SHA256 conferido), age, gitleaks, shellcheck, python3.
FROM docker.io/library/debian:trixie-slim@sha256:7378260c0a098d27ac206225db5e7d92b8c7c84ea7afccc86eeb513756bbd392

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG SOPS_VERSION=3.13.3
ARG SOPS_SHA256=e5bec3346a873ae91d871550f3e698c1aad962aff462a080e40f25fde17fef6b

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl age gitleaks shellcheck git python3 \
 && curl -fsSL -o /usr/local/bin/sops \
      "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64" \
 && echo "${SOPS_SHA256}  /usr/local/bin/sops" | sha256sum -c - \
 && chmod 0755 /usr/local/bin/sops \
 && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /work
ENTRYPOINT []
