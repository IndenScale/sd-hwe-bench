# SD-HWE-Bench piki sandbox image
# Build: docker build -f Containerfile -t sd-hwe-bench-piki:latest /path/to/piki
#
# This image contains the piki rule engine for use with --sandbox docker/podman mode.

FROM python:3.12-slim

WORKDIR /src

# Copy piki source (build context should be the piki repo root)
COPY . /src/piki

# Install local adl dependency first, then install piki in editable mode.
# piki depends on the local submodule piki/adl, not the PyPI package of the same name.
RUN pip install --no-cache-dir -e "/src/piki/adl" && \
    pip install --no-cache-dir -e "/src/piki"

# Default working directory after workspace is mounted
WORKDIR /work

# Do not set ENTRYPOINT: the runner will invoke `python -m piki <subcommand>` directly.
