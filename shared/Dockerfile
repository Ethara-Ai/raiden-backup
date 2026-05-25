# aws-cli-s3-shared — multi-stage, multi-arch base image.
#
# Stages:
#   base     - python 3.11 + system deps + moto + boto3 + pytest + aws-cli (TARGETARCH-aware)
#              + non-root agent user + shared helpers at /opt/s3rl-verifier (root, 700).
#              Not buildable as a standalone target (no entrypoint).
#   standard - default variant. Agent uses AWS_ENDPOINT_URL=http://127.0.0.1:5000
#              to reach moto. CLI submission must honor AWS_ENDPOINT_URL.
#   mitm     - mitmproxy variant. AWS_ENDPOINT_URL is unset; mitmdump on :8080
#              transparently intercepts *.s3*.amazonaws.com HTTPS and rewrites to
#              http://127.0.0.1:5000. mitmproxy CA installed into system trust
#              store at build time. Defeats simulator-detection-via-env-var.
#
# Both standard and mitm are buildable for linux/amd64 AND linux/arm64 natively
# (no Rosetta emulation) — the aws-cli download switches on TARGETARCH.
#
# Build (single arch, host-native):
#   docker build --target standard -t aws-cli-s3-shared:0.3.0      -f shared/Dockerfile .
#   docker build --target mitm     -t aws-cli-s3-shared:mitm-0.3.0 -f shared/Dockerfile .
#
# Build (multi-arch via buildx — produces manifest list; cannot --load):
#   docker buildx build --platform linux/amd64,linux/arm64 --target standard \
#       -t aws-cli-s3-shared:0.3.0 -f shared/Dockerfile .

FROM python:3.11-slim-bookworm AS base

ARG TARGETARCH
ARG MOTO_VERSION=5.2.1
ARG UV_VERSION=0.4.20
ARG AWSCLI_VERSION=2.17.0

ENV TZ=UTC \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        procps \
        tzdata \
        unzip && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv==${UV_VERSION}" && \
    pip install --no-cache-dir \
        "moto[server]==${MOTO_VERSION}" \
        "boto3==1.34.99" \
        "botocore==1.34.99" \
        "pytest==8.3.2" \
        "pytest-json-report==1.5.0" \
        "pytest-xdist==3.5.0" \
        "requests==2.32.3" \
        "hypothesis==6.108.5"

RUN case "${TARGETARCH:-amd64}" in \
        amd64) ARCH=x86_64 ;; \
        arm64) ARCH=aarch64 ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${ARCH}-${AWSCLI_VERSION}.zip" \
        -o /tmp/awscli.zip && \
    cd /tmp && unzip -q awscli.zip && \
    ./aws/install --bin-dir /opt/awsbin --install-dir /opt/aws-cli && \
    rm -rf /tmp/awscli.zip /tmp/aws && \
    chmod 700 /opt/aws-cli /opt/awsbin

ENV MOTO_S3_DEFAULT_MAX_KEYS=1000 \
    MOTO_DISABLE_GLOBAL_CORS=true \
    MOTO_S3_ALLOW_CROSSACCOUNT_ACCESS=false \
    S3_IGNORE_SUBDOMAIN_BUCKETNAME=true

ENV AWS_ACCESS_KEY_ID=testing \
    AWS_SECRET_ACCESS_KEY=testing \
    AWS_DEFAULT_REGION=us-east-1

RUN groupadd --gid 1000 s3rl && \
    useradd --create-home --shell /bin/bash --uid 1000 --gid s3rl agent && \
    mkdir -p /app && \
    chown agent:s3rl /app

COPY shared/helpers /opt/s3rl-verifier/helpers
COPY shared/reward_compute.py /opt/s3rl-verifier/reward_compute.py
COPY shared/test_base.sh /opt/s3rl-verifier/test_base.sh
RUN chmod 700 /opt/s3rl-verifier && \
    chmod -R go-rwx /opt/s3rl-verifier && \
    chown -R root:root /opt/s3rl-verifier && \
    chmod +x /opt/s3rl-verifier/test_base.sh

COPY shared/scripts/moto-startup-check.sh /usr/local/bin/moto-check
RUN chmod +x /usr/local/bin/moto-check

WORKDIR /app

FROM base AS standard

LABEL variant=standard \
      maintainer=akashdex3@gmail.com \
      org.opencontainers.image.title="aws-cli-s3-shared" \
      org.opencontainers.image.description="Base image for aws-cli-s3 Harbor RL env (standard variant: AWS_ENDPOINT_URL routes to moto)"

ENV AWS_ENDPOINT_URL=http://127.0.0.1:5000

COPY shared/scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]

FROM base AS mitm

LABEL variant=mitm \
      maintainer=akashdex3@gmail.com \
      org.opencontainers.image.title="aws-cli-s3-shared-mitm" \
      org.opencontainers.image.description="MITM variant: mitmproxy transparently rewrites *.s3*.amazonaws.com to local moto. Agent uses default AWS endpoints (no AWS_ENDPOINT_URL hint)."

RUN pip install --no-cache-dir "mitmproxy==10.4.2"

# Pre-generate mitmproxy CA at /opt/mitmproxy-ca and install into the system
# trust store at build time. Done at build (not runtime) so:
#   - first-run startup is fast
#   - the agent cannot trigger a fresh CA (would regenerate on each container
#     start, breaking the verifier session)
#   - the CA fingerprint is identical across rollouts (reproducibility)
RUN mkdir -p /opt/mitmproxy-ca && \
    chmod 755 /opt/mitmproxy-ca && \
    chown root:root /opt/mitmproxy-ca && \
    (mitmdump --set confdir=/opt/mitmproxy-ca --listen-port 18080 -q &) && \
    for i in $(seq 1 30); do \
        test -f /opt/mitmproxy-ca/mitmproxy-ca-cert.pem && break; \
        sleep 0.5; \
    done && \
    pkill -f "mitmdump.*confdir=/opt/mitmproxy-ca" 2>/dev/null || true && \
    test -f /opt/mitmproxy-ca/mitmproxy-ca-cert.pem && \
    cp /opt/mitmproxy-ca/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt && \
    update-ca-certificates && \
    chmod 644 /opt/mitmproxy-ca/mitmproxy-ca-cert.pem

COPY shared/scripts/mitm_addon.py /opt/s3rl-verifier/mitm_addon.py
COPY shared/scripts/entrypoint-mitm.sh /usr/local/bin/entrypoint-mitm.sh
COPY shared/scripts/moto-mitm-check.sh /usr/local/bin/moto-mitm-check
RUN chmod +x /usr/local/bin/entrypoint-mitm.sh /usr/local/bin/moto-mitm-check && \
    chmod 644 /opt/s3rl-verifier/mitm_addon.py

# MITM mode runtime env. The agent uses DEFAULT AWS endpoints; mitmproxy on
# 127.0.0.1:8080 transparently intercepts. NO_PROXY=127.0.0.1 ensures the
# verifier's direct boto3 calls to 127.0.0.1:5000 bypass the proxy.
# AWS_ENDPOINT_URL is empty: agent CANNOT use it as a "this is moto" signal.
ENV HTTPS_PROXY=http://127.0.0.1:8080 \
    HTTP_PROXY=http://127.0.0.1:8080 \
    NO_PROXY=127.0.0.1,localhost \
    AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    AWS_ENDPOINT_URL=

ENTRYPOINT ["/usr/local/bin/entrypoint-mitm.sh"]
CMD ["bash"]
