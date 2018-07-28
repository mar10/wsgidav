# Dockerfile for https://github.com/mar10/wsgidav/
# Build:
#   docker build --rm -f Dockerfile -t mar10/wsgidav:latest .
# Run:
#   docker run --rm -it -p <PORT>:8080 -v <ROOT_FOLDER>:/var/wsgidav-root mar10/wsgidav:latest
# for example
#   docker run --rm -it -p 8080:8080 -v c:/temp:/var/wsgidav-root mar10/wsgidav:latest
# Then open (or enter this URL in Fileexplorer or any other WebDAV client)
#   http://localhost:8080/

# NOTE 2018-07-28: alpine does not copmpile lxml
FROM python:3

EXPOSE 8080

RUN pip install wsgidav cheroot lxml
RUN mkdir -p /var/wsgidav-root

# NOTE 2018-07-28: --host localhost would not be accessible from outside
#CMD wsgidav --host localhost --port 8080 --root /var/wsgidav-root --no-config
CMD wsgidav --host 0.0.0.0 --port 8080 --root /var/wsgidav-root --no-config
