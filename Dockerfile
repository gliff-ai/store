###########################
FROM python:3.8 AS base

WORKDIR /app/

RUN mkdir etebase_server
COPY ./etebase_server/requirements.txt ./etebase_server/requirements.txt
RUN pip install -r ./etebase_server/requirements.txt

# this allows us to pip install the folder
COPY ./etebase_server ./etebase_server
COPY ./package_tools ./etebase_server
RUN pip install ./etebase_server

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY ./ /app/

CMD python /app/manage.py makemigrations && \
    python /app/manage.py migrate && \
    python /app/start.py
