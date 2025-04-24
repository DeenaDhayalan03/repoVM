FROM python:3.9

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libpq-dev \
    libcurl4-openssl-dev \
    libjpeg-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy app files
COPY . /app

# Debug-friendly pip install
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt > /tmp/reqs.log 2>&1 \
 || (echo "pip install failed. Dumping log..." && cat /tmp/reqs.log && exit 1)

# Ensure uvicorn is explicitly installed
RUN pip install --no-cache-dir uvicorn

# Expose default port
EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
