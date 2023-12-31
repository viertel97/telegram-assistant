FROM python:3.9-slim-buster

COPY . .

COPY requirements.txt .

RUN apt-get update
RUN apt-get install -y ffmpeg

RUN pip install -r requirements.txt
RUN pip install --upgrade --extra-index-url https://Quarter-Lib-Old:${PAT}@pkgs.dev.azure.com/viertel/Quarter-Lib-Old/_packaging/Quarter-Lib-Old/pypi/simple/ quarter-lib-old

RUN apt-get update && apt-get upgrade -y && apt-get install -y procps

ENV IS_CONTAINER=True

CMD ["python", "main.py"]




