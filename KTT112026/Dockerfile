FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Player DB on Railway Volume: mount path /data in the dashboard (do NOT use Docker VOLUME).
# Set: KTT_DATABASE_PATH=/data/ktt112026.db
RUN mkdir -p /data
ENV KTT_DATABASE_PATH=/data/ktt112026.db

CMD ["python", "-m", "ktt112026"]
