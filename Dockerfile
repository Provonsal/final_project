# === Stage 1: Builder ===
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app

# Жёстко отключаем user-install pip
ENV PIP_USER=0 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Создаём /root/.local заранее — чтобы копирование в runtime не упало,
# даже если pip туда ничего не положит
RUN mkdir -p /root/.local && \
    pip install --prefix=/usr/local -r requirements.txt && \
    /usr/local/bin/alembic --version

# === Stage 2: Runtime ===
FROM python:3.12-slim-bookworm AS runtime

# Создаём non-root пользователя С домашним каталогом
RUN useradd -m -s /bin/bash appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты и скрипты из builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# На случай, если pip всё-таки положил что-то в user-каталог root,
# переносим это в домашний каталог appuser
COPY --from=builder /root/.local /home/appuser/.local

# Копируем код
COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser utils/ utils/
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser alembic/ alembic/

RUN chown -R appuser:appuser /app /home/appuser \
    && chmod -R 755 /app

USER appuser

# PATH + HOME — ключевое: без HOME=... user site-packages не подхватятся
ENV PATH=/usr/local/bin:/home/appuser/.local/bin:$PATH \
    HOME=/home/appuser \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]