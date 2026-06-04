# Dockerfile for the generated CAD execution sandbox.
# This is a placeholder. Implement in the Docker sandbox milestone.

FROM python:3.11-slim

WORKDIR /work

RUN pip install --no-cache-dir cadquery

COPY execute_cadquery.py /opt/legacy_part_bench/execute_cadquery.py

ENTRYPOINT ["python", "/opt/legacy_part_bench/execute_cadquery.py"]
