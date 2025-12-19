# StreamRev Docker Image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    mariadb-client \
    redis-tools \
    ffmpeg \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /opt/streamrev

# Copy application files
COPY . /opt/streamrev/

# Create virtual environment and install dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p /var/streams/live /var/streams/vod /var/log/streamrev

# Expose ports
EXPOSE 5000 80 443

# Set up entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "-m", "src.api.server"]
