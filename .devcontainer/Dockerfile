FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y software-properties-common curl git vim libgomp1 ffmpeg \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.12 python3.12-dev python3.12-venv \
                          libgl1 libglib2.0-0 libgles2 libegl1 libglx0 \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv — avoids conflicts with apt-managed distutils packages
ENV VIRTUAL_ENV=/opt/venv
RUN python3.12 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN useradd -m -s /bin/bash ada

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /home/ada/.u2net && chown -R ada:ada /workspace /home/ada

USER ada

CMD ["bash"]
