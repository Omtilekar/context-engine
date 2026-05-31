FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY pyproject.toml ./
RUN pip install --no-cache-dir poetry==2.4.1 \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

COPY app ./app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

