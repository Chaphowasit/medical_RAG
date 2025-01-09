FROM python:3.10-slim

WORKDIR /app  
COPY .env /app
COPY requirements.txt /app 
COPY src/. /app

RUN pip install --upgrade pip && \
    pip install -r requirements.txt
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]