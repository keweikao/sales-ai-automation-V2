# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy the dependencies file (from slack_app directory)
COPY src/slack_app/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the slack_app source code
COPY src/slack_app/ .

# Run main.py when the container launches
CMD exec gunicorn --bind :$PORT --workers 2 --threads 8 --timeout 0 main:flask_app