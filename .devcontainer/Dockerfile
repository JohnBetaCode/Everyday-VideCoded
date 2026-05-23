FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash ada

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN chown -R ada:ada /workspace

USER ada

CMD ["bash"]
