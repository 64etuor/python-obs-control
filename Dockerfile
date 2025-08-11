FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# System deps (git for optional runtime git-pull entrypoint)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt ./
RUN pip install -r requirements.txt

# App code
COPY app ./app
COPY config ./config

# Optional helper scripts
COPY scripts/entrypoint-git.sh /usr/local/bin/entrypoint-git.sh
RUN chmod +x /usr/local/bin/entrypoint-git.sh || true

EXPOSE 8080

# By default, do not try to autostart desktop OBS when running in container
ENV OBS_SKIP_AUTOSTART_IN_DOCKER=1

CMD ["uvicorn", "app.presentation.app_factory:app", "--host", "0.0.0.0", "--port", "8080"]


