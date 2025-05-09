FROM python:3.10

# Install unrar to support unpacking .rar demo files.
RUN sed -i.bak 's/bullseye[^ ]* main$/& contrib non-free/g' /etc/apt/sources.list
RUN apt-get update
RUN apt-get install unrar

# Install ffmpeg.
RUN wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz
RUN tar xvf ffmpeg-git-amd64-static.tar.xz
ENV PATH="${PATH}:/ffmpeg-git-20230313-amd64-static"

# Install chromium.
RUN apt-get update -y && apt-get install -y chromium

# The --no-sandbox flag is needed by default since we execute chromium in a root environnement
RUN echo 'export CHROMIUM_FLAGS="$CHROMIUM_FLAGS --no-sandbox"' >> /etc/chromium.d/default-flags

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apt-get update && apt-get install -y python3-opencv
RUN pip install --no-cache-dir -r requirements.txt

# Install PaddleOCR for performing optical character recognition.
RUN pip install --upgrade pip setuptools wheel
COPY ocr/paddlepaddle-2.4.2-cp310-cp310-manylinux1_x86_64.whl ./
RUN pip install paddlepaddle-2.4.2-cp310-cp310-manylinux1_x86_64.whl
RUN pip install "paddleocr>=2.0.1"

# Install twitch-dl to support downloading videos from Twitch.
ENV PATH="${PATH}:/root/.local/bin"
RUN pipx install twitch-dl
RUN pipx ensurepath

# Install streamlink to support downloading streams while they are live.
RUN pip install --user -U streamlink

WORKDIR /usr/src/app/highlightly
