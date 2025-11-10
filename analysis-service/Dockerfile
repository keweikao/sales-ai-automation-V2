
# Use an official Python runtime as a parent image
FROM python:3.10-slim


# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY analysis-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY analysis-service/src/ ./src

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable for the port
ENV PORT 8080

# Run the app as a module with increased timeout for long-running analysis
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "--timeout", "600", "src.main:flask_app"]
