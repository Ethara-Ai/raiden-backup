.PHONY: help install smoke test tinker-compat \
        build build-mitm build-multi-arch build-multi-arch-mitm build-all \
        oracle-local null-local oracle-local-mitm null-local-mitm \
        all-tiers all-tiers-mitm \
        preflight preflight-mitm \
        clean

help:
	@echo "aws-cli-s3 Harbor RL environment"
	@echo ""
	@echo "Host-only (no Docker):"
	@echo "  make install                 Install dev dependencies"
	@echo "  make smoke                   Structural + schema + leakage + lint"
	@echo "  make test                    Helper unit tests"
	@echo "  make tinker-compat           Verify HarborTask structural compatibility"
	@echo ""
	@echo "Build (single-arch, native host):"
	@echo "  make build                   Standard variant (aws-cli-s3-shared:0.3.0)"
	@echo "  make build-mitm              MITM variant     (aws-cli-s3-shared:mitm-0.3.0)"
	@echo "  make build-all               Both variants"
	@echo ""
	@echo "Build (multi-arch, linux/amd64 + linux/arm64):"
	@echo "  make build-multi-arch        Standard, manifest list (cache only; --push to register)"
	@echo "  make build-multi-arch-mitm   MITM, manifest list"
	@echo ""
	@echo "E2E (needs Docker):"
	@echo "  make oracle-local            Oracle on tier1 standard"
	@echo "  make oracle-local-mitm       Oracle on tier1 against MITM image"
	@echo "  make null-local              Null agent on tier1 standard"
	@echo "  make null-local-mitm         Null agent on tier1 against MITM image"
	@echo "  make all-tiers               Oracle+null on tier1/2/3 standard"
	@echo "  make all-tiers-mitm          Oracle+null on tier1/2/3 against MITM image"
	@echo "  make preflight               Run small subset of tier1 tests against oracle"
	@echo "  make preflight-mitm          Same, against MITM image"
	@echo ""
	@echo "  make clean                   Remove caches"

install:
	pip install -r requirements-dev.txt

smoke:
	bash tools/smoke_test.sh

test:
	python3 -m pytest tools/test_helpers.py -v

tinker-compat:
	python3 tools/test_tinker_compat.py

preflight: build
	bash tools/preflight_calibrate.sh tier1

preflight-mitm: build-mitm
	S3RL_IMAGE_VARIANT=mitm bash tools/preflight_calibrate.sh tier1

build:
	bash tools/build_shared_image.sh

build-mitm:
	bash tools/build_shared_image.sh --mitm

build-multi-arch:
	bash tools/build_shared_image.sh --multi-arch

build-multi-arch-mitm:
	bash tools/build_shared_image.sh --multi-arch --mitm

build-all: build build-mitm

oracle-local: build
	bash tools/test_oracle_local.sh tier1

null-local: build
	bash tools/test_null_local.sh tier1

oracle-local-mitm: build-mitm
	S3RL_IMAGE_VARIANT=mitm bash tools/test_oracle_local.sh tier1

null-local-mitm: build-mitm
	S3RL_IMAGE_VARIANT=mitm bash tools/test_null_local.sh tier1

all-tiers: build
	@for t in tier1 tier2 tier3; do \
		echo "=== Oracle on $$t (standard) ==="; \
		bash tools/test_oracle_local.sh $$t || exit 1; \
		echo "=== Null on $$t (standard) ==="; \
		bash tools/test_null_local.sh $$t || exit 1; \
	done

all-tiers-mitm: build-mitm
	@for t in tier1 tier2 tier3; do \
		echo "=== Oracle on $$t (mitm) ==="; \
		S3RL_IMAGE_VARIANT=mitm bash tools/test_oracle_local.sh $$t || exit 1; \
		echo "=== Null on $$t (mitm) ==="; \
		S3RL_IMAGE_VARIANT=mitm bash tools/test_null_local.sh $$t || exit 1; \
	done

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .hypothesis -exec rm -rf {} +
	rm -rf out/ /tmp/s3rl-*
