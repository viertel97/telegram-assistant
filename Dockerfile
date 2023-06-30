FROM python:3.9-slim-buster

COPY . .

COPY requirements.txt .
COPY requirements_custom.txt .

RUN apt-get update
RUN apt-get install -y ffmpeg

RUN pip install -r requirements.txt
RUN pip install -r requirements_custom.txt

ENV access_id="***REMOVED***"
ENV access_key="EtZ1Tx0dZ6XMRvJTk/eyixdg1r5zmPTyolfaZ0nUxiM="

CMD ["python", "main.py"]




