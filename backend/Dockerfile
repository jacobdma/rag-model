# Prod backend image — CPU only.
#
# The LLM runs in host Ollama and the bge embedder runs on CPU (EMBED_DEVICE),
# so this image needs NO CUDA / GPU torch. That sidesteps the NVIDIA Container
# Toolkit + multi-GB cu128 nightly wheel entirely.
FROM python:3.11-slim

# tesseract-ocr backs pytesseract (OCR in the file readers).
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements.docker.txt is generated from the working venv (pip freeze) with
# the GPU torch line removed, so it's a consistent set matching dev. Install the
# CPU torch build (matching dev's 2.9.0) first, then the rest. Deps go in before
# the app code so code edits don't bust the (slow) pip layer.
COPY requirements.docker.txt ./requirements.docker.txt
RUN pip install --no-cache-dir torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.docker.txt

# App code. Data dirs + config.yaml arrive as volumes (see .dockerignore).
COPY . /app

ENV EMBED_DEVICE=cpu
EXPOSE 8000
CMD ["uvicorn", "scripts.main:app", "--host", "0.0.0.0", "--port", "8000"]
