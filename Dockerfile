FROM python:3.9-slim-buster

COPY . .

COPY requirements.txt .
COPY requirements_custom.txt .

RUN apt-get update
RUN apt-get install -y ffmpeg

RUN pip install -r requirements.txt
RUN pip install -r requirements_custom.txt

ENV IS_CONTAINER=True

CMD ["python", "main.py"]




