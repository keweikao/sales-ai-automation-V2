
# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY src/transcription/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire src directory to maintain package structure
COPY src/ ./src

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable for the port
ENV PORT 8080

# Run the app as a module to ensure relative imports work.
# Use a single worker to minimize memory usage initially.
# A longer timeout is set to handle long transcription jobs.
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "--timeout", "3600", "src.transcription.main:flask_app"]

