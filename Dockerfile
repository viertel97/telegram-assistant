ARG PYTHON_BASE=3.11-slim-bullseye
ARG PAT

FROM python:$PYTHON_BASE AS builder
ARG PAT

RUN pip install -U pdm

ENV PDM_CHECK_UPDATE=false

COPY pyproject.toml pdm.lock README.md /project/
COPY src/ /project/src

WORKDIR /project
RUN pdm install --check --prod --no-editable

FROM python:$PYTHON_BASE
RUN apt-get update && apt-get install -y ffmpeg procps flac

COPY --from=builder /project/.venv/ /project/.venv
ENV PATH="/project/.venv/bin:$PATH"
ENV PYTHONPATH="/project"

COPY src /project/src

CMD ["python", "/project/src/main.py"]