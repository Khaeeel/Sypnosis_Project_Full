FROM rocm/dev-ubuntu-22.04:6.0-complete

LABEL maintainer="cit-ai"
LABEL description="SINTOSIS-ENGINE1 RX 7900 XT OCR Pipeline"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── Critical for gfx1100 (RDNA3 / RX 7900 XT) ───────────────────────────────
ENV HSA_OVERRIDE_GFX_VERSION=11.0.0
ENV ROCR_VISIBLE_DEVICES=0
ENV HIP_VISIBLE_DEVICES=0

# ── System packages + Python 3.12 via deadsnakes PPA ─────────────────────────
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y \
    python3.12 python3.12-dev python3.12-venv \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 \
    libxrender-dev libgomp1 libfontconfig1 \
    wget curl git scrot xvfb x11-utils \
    gnome-screenshot \
    xdotool \
    python3.12-tk \
    && rm -rf /var/lib/apt/lists/*

# Install pip for 3.12 explicitly
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
RUN python3.12 -m pip install setuptools

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
 && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
 && python3.12 -m pip install --upgrade pip

# ── PyTorch with ROCm 6.0 ────────────────────────────────────────────────────
RUN pip install \
    torch==2.4.1+rocm6.0 \
    torchaudio==2.4.1+rocm6.0 \
    torchvision==0.19.1+rocm6.0 \
    --index-url https://download.pytorch.org/whl/rocm6.0

# ── PaddlePaddle (CPU — no ROCm wheel available) ─────────────────────────────
RUN pip install paddlepaddle==2.6.2

# ── OCR + Automation libs ────────────────────────────────────────────────────
RUN pip install \
    easyocr==1.7.2 \
    paddleocr==2.8.1 \
    opencv-python-headless \
    "pillow>=9.2.0" \
    pyautogui==0.9.54 \
    python-xlib \
    ollama \
    "setuptools>=65.0" \
    markdown \
    requests \
    psutil \
    imagehash \
    numpy \
    chromadb

# ── App dependencies ─────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --ignore-installed 2>/dev/null || true

# ── Source code ──────────────────────────────────────────────────────────────
COPY . .

# ── Runtime directories ──────────────────────────────────────────────────────
RUN mkdir -p \
    raw_screenshots \
    output/easyocr output/paddle output/final \
    summary/html summary/txt \
    chroma_storage

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
