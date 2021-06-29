###########################
FROM python:3.8 AS base

WORKDIR /app/

RUN mkdir etebase-server
COPY ./etebase-server/requirements.txt ./etebase-server/requirements.txt
RUN pip install -r ./etebase-server/requirements.txt

# this allows us to pip install the folder
COPY ./etebase-server ./etebase-server
COPY ./package_tools ./etebase-server
RUN pip install ./etebase-server

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY ./ /app/

CMD python /app/manage.py makemigrations && \
    python /app/manage.py migrate && \
    python /app/start.py
