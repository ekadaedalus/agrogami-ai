FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --only-binary=:all: ".[local]" && useradd --create-home agrogami
COPY docs ./docs
RUN mkdir -p /app/private_data /app/model_cache && chown -R agrogami:agrogami /app
USER agrogami
EXPOSE 8000 8501 8001
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD ["python", "-m", "uvicorn", "agrogami.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
