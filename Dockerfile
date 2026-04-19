# Dockerfile for https://github.com/mar10/wsgidav/
# Build:
#   docker build --rm -f Dockerfile -t mar10/wsgidav .
# Run (expose a root folder for anonymous access):
#   docker run --rm -it -p <PORT>:8080 -v <ROOT_FOLDER>:/public/wsgidav-share mar10/wsgidav:latest
# Run (with custom configuration file, e.g. for authentication, multiple mount-points, etc.).
# Note that the file paths in the configuration file must still be mounted into the container:
#   docker run --rm -it -v <CONFIG_FILE>:/config/wsgidav.yaml -p <PORT>:8080 -v <ROOT_FOLDER>:/public/wsgidav-share mar10/wsgidav:latest
# Examples:
#   docker run --rm -it -p 8080:8080 -v c:/temp:/public/wsgidav-share mar10/wsgidav:latest
#   docker run --rm -it -v ./wsgidav.yaml:/config/wsgidav.yaml mar10/wsgidav:latest
# Then open (or enter this URL in Windows File Explorer or any other WebDAV client)
#   http://localhost:8080/
#
# Changes:
# - 2026-03-18: support for custom configuration file and healthchecks with curl
# - 2019-11-27: smallest image generated at the end
# - 2018-07-28: alpine does not compile lxml
FROM python:3-alpine

#dependencies
RUN apk add --no-cache --virtual .build-deps gcc libxslt-dev musl-dev py3-lxml py3-pip \
    && apk --no-cache add curl \
    && pip install wsgidav cheroot lxml \
    && apk del .build-deps gcc musl-dev

RUN pip install --no-cache-dir wsgidav cheroot lxml

# This folder does not exist, so it must be mounted from the host using -v <ROOT_FOLDER>:/public/wsgidav-share
# RUN mkdir -p /public/wsgidav-share

# Create entrypoint script
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'if [ -f "/config/wsgidav.yaml" ]; then' >> /entrypoint.sh && \
    echo '  echo "Config file found, using configuration from /config/wsgidav.yaml"' >> /entrypoint.sh && \
    echo '  exec wsgidav --host=0.0.0.0 --port=8080 --config=/config/wsgidav.yaml' >> /entrypoint.sh && \
    echo 'else' >> /entrypoint.sh && \
    echo '  echo "No config file found, using default configuration"' >> /entrypoint.sh && \
    echo '  exec wsgidav --host=0.0.0.0 --port=8080 --root=/public/wsgidav-share --auth=anonymous --no-config' >> /entrypoint.sh && \
    echo 'fi' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

EXPOSE 8080

# Use entrypoint script to handle different configurations
ENTRYPOINT ["/entrypoint.sh"]
