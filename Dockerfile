# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates postgresql-client

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY k8s_crd_manager.py .
COPY *.sh .

# Make the scripts executable
RUN chmod +x k8s_crd_manager.py *.sh

# Set the entrypoint
#ENTRYPOINT ["python3", "k8s_crd_manager.py"]
ENTRYPOINT ["python3", "db-user-manager-controller.py"]
