FROM python:3.10

# Install unrar to support unpacking .rar demo files.
RUN sed -i.bak 's/bullseye[^ ]* main$/& contrib non-free/g' /etc/apt/sources.list
RUN apt-get update
RUN apt-get install unrar

# Install ffmpeg.
RUN wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz
RUN tar xvf ffmpeg-git-amd64-static.tar.xz
ENV PATH="${PATH}:/ffmpeg-git-20230313-amd64-static"

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apt-get install -y wkhtmltopdf
RUN apt-get update && apt-get install -y python3-opencv
RUN pip install --no-cache-dir -r requirements.txt

# Install twitch-dl to support downloading videos from Twitch.
ENV PATH="${PATH}:/root/.local/bin"
RUN pipx install twitch-dl
RUN pipx ensurepath

WORKDIR /usr/src/app/highlightly
