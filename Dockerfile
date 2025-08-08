FROM python:3.13.4-slim
ARG PYTHONPATH_VAR
ENV PYTHONPATH=${PYTHONPATH_VAR}
ARG PORT_VAR
ENV PORT=${PORT_VAR}

RUN apt update && \
    apt install git \
    python3-dev \
    libev-dev \
    gcc \
    -y && \
    apt clean

WORKDIR ${PYTHONPATH}
COPY . .
RUN pip3 install -r requirements.txt

CMD ["./startup.sh"]
EXPOSE ${PORT}
