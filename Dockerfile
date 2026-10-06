FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Copy project definition and readme required by hatchling build backend
COPY pyproject.toml README.md ./

# Copy application source code
COPY app/ ./app/

# Install dependencies and project package
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Expose internal service port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run FastAPI via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
