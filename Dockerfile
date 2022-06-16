###########################
FROM python:3.8-slim AS base

WORKDIR /app/

# install git and pipenv
RUN apt-get update && apt-get install --yes --no-install-recommends git
RUN pip install pipenv==2022.1.8

# install dependencies
COPY ./Pipfile /app/Pipfile
COPY ./Pipfile.lock /app/Pipfile.lock
RUN pipenv sync

# copy app files
COPY ./ /app/

EXPOSE 8000

CMD pipenv run makemigrations && \
    pipenv run migrate && \
    pipenv run update_team_storage_usage && \
    pipenv run serve
