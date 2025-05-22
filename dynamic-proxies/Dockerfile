ARG PYTHON311BASEIMAGE
FROM python:3.11-slim-bullseye AS builder
WORKDIR /code
ARG PIP_EXTRA_INDEX_VALUE
ENV UV_EXTRA_INDEX_URL=$PIP_EXTRA_INDEX_VALUE
COPY requirements.txt /code/requirements.txt
RUN pip install uv && uv venv && uv pip install -r requirements.txt && rm requirements.txt
COPY scripts/ /code/scripts
COPY app.py main.py pyproject.toml /code/

FROM $PYTHON311BASEIMAGE
RUN groupadd --gid 2000 nonroot && useradd --uid 1000 --gid 2000 -m nonroot
WORKDIR /code
COPY --from=builder /code /code
ENV PATH="/code/.venv/bin:$PATH"
USER nonroot
CMD [ "python", "app.py" ]
