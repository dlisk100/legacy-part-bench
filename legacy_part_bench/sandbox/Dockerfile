FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /work

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir cadquery

COPY sandbox/execute_cadquery.py /opt/legacy_part_bench/execute_cadquery.py

ENTRYPOINT ["python", "/opt/legacy_part_bench/execute_cadquery.py"]
