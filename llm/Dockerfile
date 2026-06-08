FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

RUN apt-get updata && apt-get install -y \
    python3 \
    python3-pip \
    gcc \
    g++ \
    curl \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY . .

ENV CUDA_VISIBLE_DEVICES=0

RUN uv sync

CMD ["uv", "run", "main.py"]