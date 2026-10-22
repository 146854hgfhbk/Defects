# Clean-room image builds for Defects4X.
#
# No prebuilt image, cache, or toolchain tarball from the reference server is
# used. Every image starts from an official base image and installs its
# dependencies from the distribution's package repository.

SHELL := /bin/bash
BUILDX ?= docker buildx build
SWIFT_IMAGE_510 ?= swift:5.10.1-jammy
SWIFT_IMAGE_61 ?= swift:6.1-jammy
SWIFT_IMAGE_623 ?= swift:6.2.3-jammy
ELIXIR_IMAGE ?= elixir:1.16.3-otp-26
SOURCE_DATE_EPOCH ?= 1760000000

SWIFT_TAGS := \
	swift-defects-validation:5.10.1-restored-20260908 \
	swift-defects-validation:6.1-recovered-20260905 \
	swift-defects-validation:6.2.3-recovered-20260906-v2 \
	swift-defects-validation:6.2.3-recovered-20260906-v3-sqlite \
	swift-defects-validation:6.2.3-recovered-20260906-v4-openssl

ELIXIR_TAGS := \
	local/defects4x/elixir-native-1.16.3-otp26:20261014 \
	local/defects4x/elixir-msz-hammox-python:20260929

.PHONY: all build swift elixir verify scan clean

all: build

build: swift elixir

swift:
	$(BUILDX) --pull --no-cache --load --provenance=true --sbom=true \
		-f swift/Dockerfile \
		--build-arg SWIFT_IMAGE=$(SWIFT_IMAGE_510) \
		--build-arg VARIANT=5.10.1-restored \
		--build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-t swift-defects-validation:5.10.1-restored-20260908 .
	$(BUILDX) --pull --no-cache --load --provenance=true --sbom=true \
		-f swift/Dockerfile \
		--build-arg SWIFT_IMAGE=$(SWIFT_IMAGE_61) \
		--build-arg VARIANT=6.1-recovered \
		--build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-t swift-defects-validation:6.1-recovered-20260905 .
	$(BUILDX) --pull --no-cache --load --provenance=true --sbom=true \
		-f swift/Dockerfile \
		--build-arg SWIFT_IMAGE=$(SWIFT_IMAGE_623) \
		--build-arg VARIANT=6.2.3-v2 \
		--build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-t swift-defects-validation:6.2.3-recovered-20260906-v2 .
	$(BUILDX) --pull --no-cache --load --provenance=true --sbom=true \
		-f swift/Dockerfile \
		--build-arg SWIFT_IMAGE=$(SWIFT_IMAGE_623) \
		--build-arg VARIANT=6.2.3-v3-sqlite \
		--build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-t swift-defects-validation:6.2.3-recovered-20260906-v3-sqlite .
	$(BUILDX) --pull --no-cache --load --provenance=true --sbom=true \
		-f swift/Dockerfile \
		--build-arg SWIFT_IMAGE=$(SWIFT_IMAGE_623) \
		--build-arg VARIANT=6.2.3-v4-openssl \
		--build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-t swift-defects-validation:6.2.3-recovered-20260906-v4-openssl .

elixir:
	$(BUILDX) --pull --no-cache --load --provenance=true --sbom=true \
		-f elixir/Dockerfile \
		--build-arg ELIXIR_IMAGE=$(ELIXIR_IMAGE) \
		--build-arg VARIANT=native \
		--build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-t local/defects4x/elixir-native-1.16.3-otp26:20261014 .
	$(BUILDX) --pull --no-cache --load --provenance=true --sbom=true \
		-f elixir/Dockerfile \
		--build-arg ELIXIR_IMAGE=$(ELIXIR_IMAGE) \
		--build-arg VARIANT=msz-python \
		--build-arg SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-t local/defects4x/elixir-msz-hammox-python:20260929 .

verify:
	@for img in $(SWIFT_TAGS); do \
		echo "== $$img"; docker run --rm $$img swift --version; \
	done
	@for img in $(ELIXIR_TAGS); do \
		echo "== $$img"; docker run --rm $$img elixir --version; \
	done

scan:
	@for img in $(SWIFT_TAGS) $(ELIXIR_TAGS); do \
		echo "== $$img"; trivy image --severity HIGH,CRITICAL $$img || true; \
	done

clean:
	docker image rm -f $(SWIFT_TAGS) $(ELIXIR_TAGS) 2>/dev/null || true
