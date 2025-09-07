# Dockerfile (Optimized Version)

FROM python:3.11-slim

# Install system dependencies required by OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Copy ONLY the requirements file first
COPY requirements.txt .

# 2. Install dependencies. This step will now be cached if requirements.txt doesn't change.
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of your application code
COPY . .

# Use the $PORT variable provided by Cloud Run
CMD exec gunicorn --bind "0.0.0.0:$PORT" --workers 1 --threads 8 --timeout 0 app:app