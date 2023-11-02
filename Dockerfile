# Base image
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

RUN mkdir /var/log/build

# Copy API server file into container
COPY api ./api
COPY model ./model
COPY static ./static

ENV HOST_DOMAIN=${HOST_DOMAIN}
ENV APP_URL_PATH=${APP_URL_PATH}
ENV STATIC_FILE_DIR=${STATIC_FILE_DIR}
ENV TORNADO_SERVER_PORT=${TORNADO_SERVER_PORT}
ENV REQUEST_LOG_FILE=${REQUEST_LOG_FILE}

ENV DIFFBOT_API_KEY=${DIFFBOT_API_KEY}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}

ENV TELNYX_API_KEY=${TELNYX_API_KEY}
ENV TELNYX_PROFILE_ID=${TELNYX_PROFILE_ID}
ENV TELNYX_PHONE_NUMBER=${TELNYX_PHONE_NUMBER}

ARG APP_URL_PATH
RUN sed -i "s#\$APP_URL_PATH#${APP_URL_PATH}#g" ./static/index.html

# Expose port for API server
EXPOSE 8888

# Start API server
CMD ["python3", "-m", "api.server"]