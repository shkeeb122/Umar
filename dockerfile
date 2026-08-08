# ============================================================
# 📁 FILE: Dockerfile
# 🎯 ROLE: Playwright + Xvfb + Gunicorn (Render Free Tier)
# 🔗 USED BY: Render Docker Environment
# ============================================================

# Playwright Official Image (Chromium + dependencies pre-installed)
FROM mcr.microsoft.com/playwright:latest

# Working Directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .

# Set Xvfb display (Virtual Framebuffer — headless browser ke liye)
ENV DISPLAY=:99

# Expose Render default port
EXPOSE 10000

# Start Xvfb in background + Gunicorn
CMD Xvfb :99 -screen 0 1280x720x16 & gunicorn --timeout=300 --workers=2 app:app
