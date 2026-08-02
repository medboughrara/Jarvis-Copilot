FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for audio and OCR
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    libasound2-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Note: For GPU support with PyTorch and Ollama, you must run this container 
# with Nvidia Container Toolkit, e.g.:
# docker run --gpus all -it jarvis_pcb_copilot
# Depending on the host, you may need a base image like nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

COPY . .

CMD ["python", "main.py"]
