# Use official Python image
FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y sqlite3 libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy code
COPY . .

# Expose Flask port
ENV PORT=8080

# Run the app
CMD ["python", "app.py"]
