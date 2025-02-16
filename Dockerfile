# pull official base image
FROM python:3.11 as backend

# to the terminal with out buffering it first
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

# prevents python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update

WORKDIR /app
COPY poetry.lock pyproject.toml /app/

# install Python Dependencies
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-root

COPY . /app

# run entrypoint.sh
#ENTRYPOINT ["/app/docker_entrypoint.sh"]
