# SD-HWE-Bench piki sandbox image
# Build: docker build -f Containerfile -t sd-hwe-bench-piki:latest /path/to/piki
#
# This image contains the piki rule engine for use with --sandbox docker/podman mode.

ARG PYTHON_BASE_IMAGE=python:3.12-slim
ARG WORKDIR_SRC=/src
ARG WORKDIR_RUN=/work
ARG PIKI_INSTALL_DIR=/src/piki

FROM ${PYTHON_BASE_IMAGE}

ARG WORKDIR_SRC
ARG WORKDIR_RUN
ARG PIKI_INSTALL_DIR

WORKDIR ${WORKDIR_SRC}

# Copy piki source (build context should be the piki repo root)
COPY . ${PIKI_INSTALL_DIR}

# Install local adl dependency first, then install piki in editable mode.
# piki depends on the local submodule piki/adl, not the PyPI package of the same name.
RUN pip install --no-cache-dir -e "${PIKI_INSTALL_DIR}/adl" && \
    pip install --no-cache-dir -e "${PIKI_INSTALL_DIR}"

# Default working directory after workspace is mounted
WORKDIR ${WORKDIR_RUN}

# Do not set ENTRYPOINT: the runner will invoke `python -m piki <subcommand>` directly.
