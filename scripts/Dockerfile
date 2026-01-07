FROM python:3.10-slim
WORKDIR /app

# Install minimal runtime deps for scripts
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the replayer
COPY replay.py ./

# Defaults can be overridden via docker-compose command/env
ENV DURATION_HOURS=24 \
    HOME_ID=home_001 \
    BROKER_HOST=mosquitto \
    BROKER_PORT=1883

CMD ["sh", "-c", "python replay.py --mode synthetic --duration ${DURATION_HOURS} --home-id ${HOME_ID} --broker ${BROKER_HOST} --port ${BROKER_PORT}"]
