FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["sh", "-c", "uvicorn proofline.main:app --host 0.0.0.0 --port ${PORT}"]
