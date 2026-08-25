FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg espeak-ng fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Railway cron re-runs this on schedule (see README "Deploy" section).
# Each run tops up the backlog (if ANTHROPIC_API_KEY is set), renders
# whatever's newly "scripted", then exits — no long-lived process needed.
CMD ["python3", "daily.py"]
