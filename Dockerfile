FROM python:3.6.9

RUN mkdir /app
WORKDIR /app

COPY main.py main.py
COPY setup.py setup.py
COPY README.md README.md

RUN python setup.py install
RUN mkdir ~/.coach/
RUN echo '{}' > ~/.coach/creds.json