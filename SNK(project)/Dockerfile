# ==============================================================================
# Faculty Attendance, Leave & Substitute Management ERP — Web Microservice
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered terminal logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

WORKDIR /app

# Install minimal OS dependencies for network & cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose web service and biometric kiosk bridge port
EXPOSE 8000

# Healthcheck to monitor endpoint availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/status || exit 1

# Launch ASGI Web Server using Uvicorn
CMD ["uvicorn", "services.mobile_punch_service:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
