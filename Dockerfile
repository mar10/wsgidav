# Dockerfile for https://github.com/mar10/wsgidav/
# Build:
#   docker build --rm -f Dockerfile -t mar10/wsgidav .
# Run:
#   docker run --rm -it -p <PORT>:8080 -v <ROOT_FOLDER>:/var/wsgidav-root mar10/wsgidav
# for example
#   docker run --rm -it -p 8080:8080 -v c:/temp:/var/wsgidav-root mar10/wsgidav
# Then open (or enter this URL in Windows File Explorer or any other WebDAV client)
#   http://localhost:8080/

FROM python:3-alpine

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
RUN apk add --no-cache --virtual .build-deps gcc libxslt-dev musl-dev py3-lxml \
    && uv pip install --system wsgidav cheroot lxml \
    && apk del .build-deps gcc musl-dev

RUN mkdir -p /var/wsgidav-root

EXPOSE 8080

# Define the command to run WsgiDAV
CMD ["wsgidav", "--host=0.0.0.0", "--port=8080", "--root=/var/wsgidav-root", "--auth=anonymous", "--no-config"]
