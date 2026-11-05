# syntax=docker/dockerfile:1
# Unofficial, source-pinned recipe; validated source commits, not fully hermetic.

FROM maven:3.9-eclipse-temurin-21 AS kroki-builder
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 --branch v0.34.0 https://github.com/yuzutech/kroki.git kroki \
    && test "$(git -C kroki rev-parse HEAD)" = "2408475da7877125364abcd4c1c9fabf02a8756c"
WORKDIR /src/kroki
COPY patches/kroki-server-pom.patch /tmp/kroki-server-pom.patch
RUN git apply --check /tmp/kroki-server-pom.patch \
    && git apply /tmp/kroki-server-pom.patch \
    && mvn -B -ntp -pl server -am clean verify \
    && test -s server/target/kroki-server.jar

FROM golang:1.27.3 AS d2-builder
ENV GOTOOLCHAIN=local
RUN apt-get update && apt-get install -y --no-install-recommends git jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 --branch v0.9.0 https://github.com/terrastruct/d2.git d2 \
    && test "$(git -C d2 rev-parse HEAD)" = "d5a51743b6d5c00f1ec6f8340003f5d5a6ba4eda"
WORKDIR /src/d2
COPY patches/d2-go-mod.patch /tmp/d2-go-mod.patch
RUN git apply --check /tmp/d2-go-mod.patch \
    && git apply /tmp/d2-go-mod.patch \
    && go mod tidy \
    && go mod verify \
    && go test ./...
RUN CGO_ENABLED=0 go build -trimpath -o /out/d2 .

FROM golang:1.27.3 AS goat-builder
ENV GOTOOLCHAIN=local
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 --branch v0.5.1 https://github.com/blampe/goat.git goat \
    && test "$(git -C goat rev-parse HEAD)" = "6d4db359c601eae6efa1fcd94601fa1793e114d5"
WORKDIR /src/goat
RUN CGO_ENABLED=0 go build -trimpath -o /out/goat ./cmd/goat

FROM eclipse-temurin:21.0.13_9-jre-noble AS patched-java

# Digest observed for the official 0.34.0 image during the initial review.
FROM yuzutech/kroki:0.34.0@sha256:1314e60e6dd813cd00c90cb22007a05fdb92edf43259dfae71abbe89429ea36a

USER root

# Replaces the effective Java runtime, but does not remove base image layers.
RUN rm -rf /opt/java/openjdk
COPY --from=patched-java /opt/java/openjdk /opt/java/openjdk
ENV JAVA_VERSION=jdk-21.0.13+9

# Ubuntu package state intentionally follows available security updates.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=kroki-builder --chown=kroki:kroki \
    /src/kroki/server/target/kroki-server.jar /usr/local/kroki/kroki-server.jar
COPY --from=d2-builder /out/d2 /usr/bin/d2
COPY --from=goat-builder /out/goat /usr/bin/goat

ENV KROKI_SAFE_MODE=secure
USER kroki
# Keep the original image entrypoint, exposed port, and renderer configuration.
