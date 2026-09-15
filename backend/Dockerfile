FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the backend code and the raw data
COPY backend/ /app/backend/
COPY data/ /app/data/

ENV PYTHONPATH=/app/backend
WORKDIR /app/backend

EXPOSE 8000

# Start the FastAPI server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
