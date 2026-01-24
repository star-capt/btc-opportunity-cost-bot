FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV DATABASE_PATH=/data/bot.db

# Create data directory for volume mount
RUN mkdir -p /data

CMD ["python", "-m", "bot.main"]
