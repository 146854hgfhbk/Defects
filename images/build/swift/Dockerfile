# syntax=docker/dockerfile:1.7
# Clean-room Swift runtime for Defects4X.
#
# The base image is an official Swift image. No binary, cache, or toolchain
# tarball from the compromised reference server is used.
ARG SWIFT_IMAGE=swift:6.2.3-jammy
FROM ${SWIFT_IMAGE}

ARG VARIANT=clean
ARG SOURCE_DATE_EPOCH=1760000000

LABEL org.opencontainers.image.title="Defects4X Swift runtime (clean rebuild)"
LABEL org.opencontainers.image.description="Clean-room Swift runtime for Defects4X Swift cases"
LABEL defects4x.variant="${VARIANT}"
LABEL defects4x.rebuilt_from_source="true"

USER root
ENV DEBIAN_FRONTEND=noninteractive
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        libsqlite3-dev \
        libncurses-dev \
        libarchive-dev \
        libssl-dev \
        libcurl4-openssl-dev \
        libxml2-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
CMD ["/bin/bash"]
