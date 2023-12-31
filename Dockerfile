FROM python:3.9-slim-buster
ARG PAT

COPY . .

COPY requirements.txt .

RUN apt-get update
RUN apt-get install -y ffmpeg
RUN apt-get upgrade -y && apt-get install -y procps

RUN pip install -r requirements.txt
RUN pip install --upgrade --extra-index-url https://Quarter-Lib-Old:${PAT}@pkgs.dev.azure.com/viertel/Quarter-Lib-Old/_packaging/Quarter-Lib-Old/pypi/simple/ quarter-lib-old


ENV IS_CONTAINER=True

CMD ["python", "main.py"]




