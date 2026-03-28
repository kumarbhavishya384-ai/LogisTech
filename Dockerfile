FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install with cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port
EXPOSE 7860

# Start server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
