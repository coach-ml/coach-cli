FROM python:3.7

RUN mkdir /app
WORKDIR /app

COPY main.py main.py
COPY setup.py setup.py
COPY README.md README.md

RUN pip install -e .
RUN mkdir ~/.coach/
RUN echo '{}' > ~/.coach/creds.json