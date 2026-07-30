# syntax=docker/dockerfile:1
#
# Sparkle — production image (owner: Ashish)
# Multi-stage build: a "builder" stage installs Python dependencies into an
# isolated prefix; the final stage starts fresh from the same slim base and
# copies over ONLY that installed prefix plus the app code. Pip's own
# install machinery, build metadata, and cache never end up in the image
# that actually ships — smaller image, smaller attack surface.

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# Installed into /install instead of the system site-packages, so stage 2
# can copy just this folder over and leave pip/setuptools/wheel behind.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: final ----------
FROM python:3.12-slim

# PYTHONUNBUFFERED  -> logs stream out immediately (needed for docker logs)
# PYTHONDONTWRITEBYTECODE -> no .pyc clutter in the image
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Bring in ONLY the installed packages from the builder stage — not pip's
# cache, not build metadata, not the requirements.txt install step itself.
COPY --from=builder /install /usr/local

# --- unprivileged user ---
RUN useradd --create-home --shell /usr/sbin/nologin appuser
RUN mkdir -p /app/instance && chown -R appuser:appuser /app

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
     "--preload", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:create_app()"]
