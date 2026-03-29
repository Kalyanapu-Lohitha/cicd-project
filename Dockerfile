FROM python:3.11-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 5000

RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]