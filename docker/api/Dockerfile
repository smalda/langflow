FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make sure migrations folder exists
RUN mkdir -p alembic/versions

# Command to run migrations and start the application
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
