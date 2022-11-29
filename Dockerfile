FROM python:3.9-slim-buster

WORKDIR /code

COPY requirements.txt .

RUN apt-get update
RUN apt-get install -y build-essential ffmpeg

