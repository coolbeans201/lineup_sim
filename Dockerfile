FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src ./src
COPY app ./app
COPY data/presets ./data/presets
COPY scripts ./scripts

ENV PYTHONPATH=/app/src
EXPOSE 8501

# Bundled player data is not in the image — mount data/ or run bootstrap after start.
CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
