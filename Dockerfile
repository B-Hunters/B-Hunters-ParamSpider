FROM python:3.12-slim

# Copy Go binaries and tools from the build stage
RUN apt update &&  apt install git -y && apt clean && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/bormaa/ParamSpider /app/paramspider
WORKDIR /app/paramspider
RUN pip install .
RUN pip install --no-cache-dir b-hunters==1.1.0

WORKDIR /app/service

# Copy necessary files
COPY paramspiderm paramspiderm

# Default command
CMD ["python3", "-m", "paramspiderm"]
