FROM mcr.microsoft.com/playwright:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["gunicorn", "--timeout=300", "--workers=2", "app:app"]
