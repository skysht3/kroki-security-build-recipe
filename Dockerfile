# syntax=docker/dockerfile:1
# Unofficial Linux/amd64 build. Keep the patched upstream image as the runtime.

FROM maven:3.9-eclipse-temurin-21 AS kroki-builder
# The upstream Maven tests render PlantUML/Structurizr fixtures.
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates graphviz fontconfig fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src/kroki
RUN git clone --depth 1 --branch v0.37.1 https://github.com/yuzutech/kroki.git . \
    && test "$(git rev-parse HEAD)" = "aaa288dd1c262a52de9f55b67df0700d7d97ba1e"
COPY patches/kroki-server-pom.patch /tmp/kroki-server-pom.patch
RUN git apply --check /tmp/kroki-server-pom.patch \
    && git apply /tmp/kroki-server-pom.patch \
    && mvn -B -ntp -pl server -am clean verify \
    && test -s server/target/kroki-server.jar

FROM golang:1.27.4 AS d2-builder
ENV GOTOOLCHAIN=local
RUN apt-get update && apt-get install -y --no-install-recommends git jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src/d2
RUN git clone --depth 1 --branch v0.9.0 https://github.com/d2lang/d2.git . \
    && test "$(git rev-parse HEAD)" = "d5a51743b6d5c00f1ec6f8340003f5d5a6ba4eda"
# The Kroki server requires this upstream D2 patch in secure/safe modes.
COPY --from=kroki-builder /src/kroki/server/ops/docker/d2/local-files.patch /tmp/d2-local-files.patch
COPY patches/d2-go-mod.patch /tmp/d2-go-mod.patch
RUN git apply --check /tmp/d2-local-files.patch /tmp/d2-go-mod.patch \
    && git apply /tmp/d2-local-files.patch /tmp/d2-go-mod.patch \
    && go mod tidy \
    && go mod verify \
    && go test ./... \
    && CGO_ENABLED=0 go build -mod=readonly -trimpath \
        -ldflags "-s -w -X github.com/d2lang/d2/lib/version.Version=v0.9.0" \
        -o /out/d2 . \
    && go version -m /out/d2 | grep -Eq '^[[:space:]]+dep[[:space:]]+golang.org/x/net[[:space:]]+v0\.62\.0[[:space:]]' \
    && /out/d2 --help 2>&1 | grep -- '--allow-local-files'

# Official 0.37.1 amd64 manifest; Ubuntu 26.04, Temurin 21.0.13.1+2.
FROM yuzutech/kroki:0.37.1@sha256:3767ff52c85dcd0986c9e286b5409c8f4f79d937a1f3bd8f3afc63f2a2ad46ce
COPY --from=kroki-builder --chown=kroki:kroki \
    /src/kroki/server/target/kroki-server.jar /usr/local/kroki/kroki-server.jar
COPY --from=d2-builder /out/d2 /usr/bin/d2
ENV KROKI_SAFE_MODE=secure
# Inherits the runtime user, command, and tools from this official image.
