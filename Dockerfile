FROM python:3.10

# Add unrar to support unpacking .rar demo files.
RUN sed -i.bak 's/bullseye[^ ]* main$/& contrib non-free/g' /etc/apt/sources.list
RUN apt-get update
RUN apt-get install unrar

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /usr/src/app/highlightly
