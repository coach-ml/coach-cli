FROM python:3.6.9

RUN mkdir /app
WORKDIR /app

RUN apt-get update
RUN apt-get install -y vim

COPY main.py main.py
COPY setup.py setup.py
COPY README.md README.md

RUN pip install -e .
RUN mkdir ~/.coach/
RUN echo '{}' > ~/.coach/creds.json