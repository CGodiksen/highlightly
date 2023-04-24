FROM python:3.10

# Install unrar to support unpacking .rar demo files.
RUN sed -i.bak 's/bullseye[^ ]* main$/& contrib non-free/g' /etc/apt/sources.list
RUN apt-get update
RUN apt-get install unrar

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg and twitch-dl to support downloading videos from Twitch.
ENV PATH="${PATH}:/root/.local/bin"
RUN apt-get install -y ffmpeg
RUN pipx install twitch-dl
RUN pipx ensurepath

WORKDIR /usr/src/app/highlightly
