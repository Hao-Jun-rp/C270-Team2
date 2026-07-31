# syntax=docker/dockerfile:1
#
# Sparkle — production image (owner: Ashish)
#
# Design notes (worth saying out loud in the demo):
#  * python:3.12-slim keeps the base small.
#  * We install NO apt build tools. Our only non-pure-Python dependency is
#    `cryptography`, which ships prebuilt manylinux wheels, and our MySQL
#    driver is PyMySQL (pure Python). Adding build-essential +
#    default-libmysqlclient-dev would only be needed for `mysqlclient`,
#    which we don't use — it added several hundred MB for nothing.
#  * requirements.txt is copied and installed BEFORE the source code, so
#    Docker's layer cache only reinstalls dependencies when they change.
#  * The container runs as a non-root user (defence in depth: if the app is
#    ever compromised, the attacker isn't root inside the container).
#  * No secrets are baked in. .dockerignore excludes .env and certs/;
#    config is injected as environment variables at runtime.

FROM python:3.12-slim

# PYTHONUNBUFFERED  -> logs stream out immediately (needed for docker logs)
# PYTHONDONTWRITEBYTECODE -> no .pyc clutter in the image
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# --- dependencies first (cached layer) ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- unprivileged user ---
RUN useradd --create-home --shell /usr/sbin/nologin appuser

# --- application code ---
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Gunicorn is a production WSGI server; Flask's built-in server is
# single-threaded and explicitly not for production use.
#   --workers 2      handle concurrent requests (rule of thumb: 2*CPU+1)
#   --timeout 60     kill stuck workers
#   --access-logfile/--error-logfile "-"  send logs to stdout/stderr so
#                    `docker logs` and CloudWatch can collect them
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:create_app()"]
