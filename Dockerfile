FROM python:3.12-slim

# Copy Go binaries and tools from the build stage
RUN apt update &&  apt install git -y && apt clean && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/bormaa/ParamSpider /app/paramspider
WORKDIR /app/paramspider
RUN pip install .
# The shared class is built from this repository, not from the published
# release: a worker that calls auth_headers(task) against a release that
# does not have it fails inside the scan.  scripts/build_workers.sh passes
# the local wheel; the default is the published release.
ARG B_HUNTERS_WHEEL=b-hunters==1.2.0
RUN pip install --no-cache-dir ${B_HUNTERS_WHEEL}

WORKDIR /app/service

# Copy necessary files
COPY paramspiderm paramspiderm

# Default command
CMD ["python3", "-m", "paramspiderm"]
