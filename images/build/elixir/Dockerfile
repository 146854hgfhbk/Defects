# syntax=docker/dockerfile:1.7
# Clean-room Elixir runtime for Defects4X.
#
# The base image is an official Elixir image. No binary, cache, or toolchain
# tarball from the compromised reference server is used.
ARG ELIXIR_IMAGE=elixir:1.16.3-otp-26
FROM ${ELIXIR_IMAGE}

ARG VARIANT=native
ARG SOURCE_DATE_EPOCH=1760000000

LABEL org.opencontainers.image.title="Defects4X Elixir runtime (clean rebuild)"
LABEL org.opencontainers.image.description="Clean-room Elixir runtime for Defects4X Elixir cases"
LABEL defects4x.variant="${VARIANT}"
LABEL defects4x.rebuilt_from_source="true"

USER root
ENV DEBIAN_FRONTEND=noninteractive
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}
ENV MIX_ENV=test

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        curl \
        python3 \
        python3-pip \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN mix local.hex --force && mix local.rebar --force

WORKDIR /work
CMD ["/bin/bash"]
