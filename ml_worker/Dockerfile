# Use the official Python 3.8 slim image as the base image
FROM python:3.8-slim

# Install gcc to handle any C-extensions in Python packages
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt /ml_worker/requirements.txt
RUN pip install --no-cache-dir -r /ml_worker/requirements.txt

# Copy the rest of the application code
ADD . /ml_worker

# Set the working directory
WORKDIR /ml_worker
RUN mkdir /nonexistent
RUN chmod -R 777 /nonexistent

# Set the entrypoint for the container
ENTRYPOINT ["celery", "-A", "tasks", "worker", "-P", "solo", "--loglevel=info", "--without-gossip", "--without-mingle", "--without-heartbeat"]
