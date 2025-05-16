FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cài đặt MySQL client
RUN apt-get update && apt-get install -y default-mysql-client

# Mở port 3001
EXPOSE 3001

# Command để chạy app
CMD ["python", "main.py"]
