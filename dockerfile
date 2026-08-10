# ============================================================
# DOCKERFILE — ULTIMATE RENDER CHROME SETUP
# 100% Working — All Dependencies Included
# ============================================================

FROM python:3.10-slim

# ------------------------------------------------------------
# LAYER 1: Install ALL System Dependencies + Chrome
# ------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    # Chrome ke liye MUST libraries (20+)
    wget \
    gnupg \
    curl \
    unzip \
    xvfb \
    libnss3 \
    libx11-6 \
    libgbm1 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxshmfence1 \
    libxfixes3 \
    libxrender1 \
    libxi6 \
    libxtst6 \
    libgl1-mesa-glx \
    libxcomposite-dev \
    libxdamage-dev \
    libxrandr-dev \
    libx11-dev \
    libxcb-shm0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    libxcb-xkb1 \
    libx11-xcb1 \
    libxcb1 \
    libxcb-xkb1 \
    libxcb-xv0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-util1 \
    libxcb-render0 \
    libxcb-render-util0 \
    libxcb-xinput0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxcb-xv0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-util1 \
    libxcb-render0 \
    libxcb-render-util0 \
    libxcb-xinput0 \
    --no-install-recommends \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# LAYER 2: Python Dependencies (Minimal)
# ------------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------
# LAYER 3: Source Code
# ------------------------------------------------------------
COPY . .

# ------------------------------------------------------------
# LAYER 4: Environment Variables (Render Dashboard override)
# ------------------------------------------------------------
ENV CHROME_PATH=/usr/bin/google-chrome-stable
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV TZ=UTC

# ------------------------------------------------------------
# LAYER 5: Start (Gunicorn)
# ------------------------------------------------------------
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--workers", "2", "--threads", "4"]
