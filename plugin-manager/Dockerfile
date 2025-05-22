ARG PYTHON311BASEIMAGE
FROM python:3.11-slim-bullseye AS builder
WORKDIR /code
ARG PIP_EXTRA_INDEX_VALUE
ENV UV_EXTRA_INDEX_URL=$PIP_EXTRA_INDEX_VALUE

COPY requirements.txt /code/requirements.txt
RUN pip install uv && uv venv && uv pip install -r requirements.txt && rm requirements.txt
RUN uv pip install kfp==2.8.0
COPY scripts/ /code/scripts
COPY templates/ /code/templates
COPY __version__.py app.py main.py pyproject.toml /code/

FROM golang:1.24.2 AS gobuilder
WORKDIR /code
RUN apt-get update && apt-get install -y git
RUN git clone -b v2.5.0 https://github.com/sigstore/cosign.git /code/cosign/
WORKDIR /code/cosign
RUN go install ./cmd/cosign

FROM $PYTHON311BASEIMAGE
COPY --from=gobuilder /go/bin/cosign /usr/local/bin/cosign
RUN apt-get update && apt-get install -y curl git &&\
    git config --global core.symlinks false &&\
    # curl -O -L "https://azrabsilensqa01.blob.core.windows.net/binaries/cosign-2.4.0" &&\
    # mv cosign-2.4.0 /usr/local/bin/cosign &&\
    chmod +x /usr/local/bin/cosign &&\
    apt-get remove --purge -y curl &&\
    rm -rf /var/lib/apt/lists/*
WORKDIR /code
RUN mkdir -p /code/keys
COPY --from=builder /code /code
ENV PATH="/code/.venv/bin:$PATH"
USER  nonroot
CMD [ "python", "app.py" ]
