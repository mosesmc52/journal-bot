# pull official base image
FROM python:3.7-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


RUN mkdir /media
WORKDIR /app
COPY ./Pipfile ./
COPY ./Pipfile.lock ./

RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile
RUN rm Pipfile
RUN rm Pipfile.lock

COPY  . .
