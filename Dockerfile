FROM python:3.12-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Apply OS security updates
RUN apk update && apk upgrade --no-cache

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure directories exist and run as a non-privileged user
RUN mkdir -p static/uploads instance \
    && addgroup -S rotaract \
    && adduser -S rotaract -G rotaract -h /app \
    && chown -R rotaract:rotaract /app

USER rotaract

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]


