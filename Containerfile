# SD-HWE-Bench piki sandbox image
# Build: docker build -f Containerfile -t sd-hwe-bench-piki:latest /path/to/piki
#
# This image contains the piki rule engine used by the --sandbox docker/podman mode.

FROM python:3.12-slim

WORKDIR /src

# Copy piki source (expects build context to be the piki repository root)
COPY . /src/piki

# Install piki in editable mode so it picks up the local aql package
RUN pip install --no-cache-dir -e "/src/piki"

# Default working directory for mounted workspaces
WORKDIR /work

ENTRYPOINT ["python", "-m", "piki"]
