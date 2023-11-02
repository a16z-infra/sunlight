source service.cfg

# Build the Docker image
docker build \
  -t sunlight \
  --build-arg APP_URL_PATH=$APP_URL_PATH \
  .

# Run the Docker container and map port 8888 to the host
docker run \
  -p 8888:8888 \
  -e HOST_DOMAIN=$HOST_DOMAIN \
  -e APP_URL_PATH=$APP_URL_PATH \
  -e STATIC_FILE_DIR=$STATIC_FILE_DIR \
  -e TORNADO_SERVER_PORT=$TORNADO_SERVER_PORT \
  -e REQUEST_LOG_FILE=$REQUEST_LOG_FILE \
  -e DIFFBOT_API_KEY=$DIFFBOT_API_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN \
  -e TELNYX_API_KEY=$TELNYX_API_KEY \
  -e TELNYX_PROFILE_ID=$TELNYX_PROFILE_ID \
  -e TELNYX_PHONE_NUMBER=$TELNYX_PHONE_NUMBER \
  sunlight
