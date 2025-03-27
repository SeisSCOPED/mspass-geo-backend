# Use Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy app code and dependency files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask port
EXPOSE 5050

# Load env variables & run app
CMD ["sh", "-c", "python app.py"]
