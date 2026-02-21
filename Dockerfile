# ═══════════════════════════════════════════════════════════════
#  Stage 1 — Builder: install Python dependencies
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ═══════════════════════════════════════════════════════════════
#  Stage 2 — Runtime: lean final image
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Directory for SQLite database persistence
RUN mkdir -p /app/data

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Default env (override with --env-file .env)
ENV DATABASE_URL=sqlite+aiosqlite:///./data/agent_platform.db \
    APP_ENV=production

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
