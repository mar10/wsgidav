FROM python:3
# FROM python:3-slim
# alpine does not copmpile lxml
#FROM python:3.7-alpine3.8
EXPOSE 8080
RUN pip install wsgidav cheroot lxml
# RUN python -m pip install wsgidav cheroot lxml
# CMD ["wsgidav", "--version", "-v"]
CMD wsgidav --host 0.0.0.0 --port 8080 --root . --no-config
