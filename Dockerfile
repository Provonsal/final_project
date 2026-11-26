# === Stage 1: Builder ===
FROM python:3.12-slim-bookworm AS builder

# 1. Устанавливаем зависимости для компиляции (нужны только здесь)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Создаем виртуальное окружение в нейтральной директории
RUN python -m venv /opt/venv

# 3. Активируем его для всех последующих команд в этом этапе
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .

# 4. Обновляем pip и ставим зависимости строго в venv (без кэша для экономии места)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# === Stage 2: Runtime ===
FROM python:3.12-slim-bookworm AS runtime

# 1. Только runtime-зависимости (без компиляторов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 2. Создаем непривилегированного пользователя
RUN useradd -m -s /bin/bash appuser

# 3. Копируем готовое виртуальное окружение из builder
# (Это работает, потому что базовые образы идентичны)
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# 4. Копируем код приложения
COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser utils/ utils/
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser alembic/ alembic/

# 5. НАДЕЖНО отдаем права на venv и код нашему пользователю
RUN chown -R appuser:appuser /opt/venv /app

# 6. Переключаемся на пользователя (все дальше выполняется от его имени)
USER appuser

# 7. Указываем PATH, чтобы команды python и uvicorn брались из venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 8. Запускаем
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]