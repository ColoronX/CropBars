FROM python:3.10-slim

# Install ffmpeg AND standard SSL certificates
RUN apt-get update && \
    apt-get install -y ffmpeg ca-certificates && \
    update-ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install them
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY --chown=user . .

# Run the bot
CMD ["python", "main.py"]