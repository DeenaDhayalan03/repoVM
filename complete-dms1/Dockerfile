FROM python:3.9

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libpq-dev \
    libcurl4-openssl-dev \
    libjpeg-dev

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir uvicorn

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
