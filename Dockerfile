FROM python:3.9-alpine

COPY requirements.txt requirements.txt
COPY dumbidiot.py dumbidiot.py

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "dumbidiot.py"]
