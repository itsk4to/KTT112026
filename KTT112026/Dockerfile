FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Runtime deps only (game code runs from /app/src so JSON data is always present)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md VERSION.txt ./
COPY src ./src

# Prefer source tree over site-packages (includes game/content/data/*.json)
ENV PYTHONPATH=/app/src
ENV KTT_DATABASE_PATH=/data/ktt112026.db

RUN mkdir -p /data \
    && python -c "from pathlib import Path; p=Path('/app/src/ktt112026/game/content/data'); assert (p/'vukhi.json').is_file(), p; print('content ok', len(list(p.glob('*.json'))), 'json')"

CMD ["python", "-m", "ktt112026"]
