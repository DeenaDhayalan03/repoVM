FROM python:3.9

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libpq-dev \
    libcurl4-openssl-dev \
    libjpeg-dev

RUN pip install --no-cache-dir -r requirements.txt | tee /tmp/pip_install.log || (echo "Error with pip install" && cat /tmp/pip_install.log)

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
