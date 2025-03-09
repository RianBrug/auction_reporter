FROM python:3.11-slim

WORKDIR /app

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && apt-get clean

# Copy project files
COPY requirements.txt .
COPY src/ src/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DOCKER_ENV=true

# Create a non-root user to run the app
RUN useradd -m appuser
USER appuser

CMD ["python", "src/local.py"] 