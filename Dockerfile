FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY src/ src/
ENV PYTHONPATH=/app/src
ENV OUTPUT_DIR=/output

ENTRYPOINT ["python", "-m", "stylometry.cli"]
