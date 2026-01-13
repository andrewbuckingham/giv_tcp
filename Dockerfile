# givtcp-vuejs builder
FROM node:current-alpine AS givtcp_vuejs_tmp

# set the working directory in the container
WORKDIR /app

# Copy file dependencies in a single layer
COPY givtcp-vuejs .

RUN npm install && \
    npm run build && \
    mv dist/index.html dist/config.html

# set base image (host OS)
#FROM python:3.11-rc-alpine
FROM python:alpine3.19

RUN apk add --no-cache \
    git \
    mosquitto \
    musl \
    nginx \
    redis \
    tzdata \
    xsel

RUN mkdir -p /run/nginx

# set the working directory in the container
WORKDIR /app

# copy the dependencies file to the working directory
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY ingress.conf /etc/nginx/http.d/
COPY ingress_no_ssl.conf /app/ingress_no_ssl.conf
RUN rm /etc/nginx/http.d/default.conf

# copy the content of the local src directory to the working directory
COPY GivTCP/ ./GivTCP
COPY WebDashboard ./WebDashboard
# COPY givenergy_modbus/ /usr/local/lib/python3.11/site-packages/givenergy_modbus
COPY GivTCP/givenergy_modbus_async/ /usr/local/lib/python3.12/site-packages/givenergy_modbus_async

COPY api.json ./GivTCP/api.json
COPY startup.py startup.py
COPY redis.conf redis.conf
COPY settings.json ./settings.json
COPY ingress/ ./ingress

# Copy static site files
COPY --from=givtcp_vuejs_tmp /app/dist /app/ingress/

# Environment variables for Phase 1-5 refactoring feature flags
# Phase 2: Cache Repository
ENV USE_NEW_CACHE="false"
# Phase 5: Lock Manager
ENV USE_NEW_LOCKS="false"
# Phase 3: Service Layer
ENV USE_NEW_SERVICES="false"

# Standard GivTCP environment variables
ENV INVERTOR_IP="" \
    INVERTOR_NUM_BATTERIES="0" \
    MQTT_ADDRESS="127.0.0.1" \
    MQTT_USERNAME="" \
    MQTT_PASSWORD="" \
    MQTT_TOPIC="GivEnergy" \
    HA_AUTO_D="True" \
    LOG_LEVEL="Info" \
    PRINT_RAW="False" \
    SELF_RUN_LOOP_TIMER="5" \
    QUEUE_RETRIES="2" \
    CACHELOCATION="/config"

EXPOSE 1883 3000 6379 8099

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:6345/readData || exit 1

CMD ["python3", "/app/startup.py"]