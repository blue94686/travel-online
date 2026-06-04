FROM python:3.11-slim

WORKDIR /app/backend

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8000

# Run with Gunicorn. Keep the default at one worker so startup migrations are not run concurrently.
CMD ["sh", "-c", "gunicorn app.main:app -w ${WEB_CONCURRENCY:-1} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --access-logfile - --error-logfile -"]
