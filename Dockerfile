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

# Install native alpine lxml
RUN apk --no-cache add py-lxml

RUN pip install --no-cache-dir wsgidav cheroot
RUN mkdir -p /var/wsgidav-root

EXPOSE 8080

CMD wsgidav --host 0.0.0.0 --port 8080 --root /var/wsgidav-root --no-config
