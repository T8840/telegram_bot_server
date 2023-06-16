FROM python:3.10-slim

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 && rm -rf /var/lib/apt/lists/*
COPY ./app /app
WORKDIR /app/

ENV PYTHONPATH=/app

EXPOSE 5000:5000
CMD ["python","tg_bot.py"]
