FROM python:3-alpine

WORKDIR /usr/src/app

ENV USER ""
ENV PASSWORD ""

ENV MESSAGE_TYPES "locking:Sperrung;obstruction:Gefahrenstelle;narrowing:Fahrbahnverengung;others:Sonstige"

#az storage account show-connection-string -g <ResourceGroup> -n <Resource-Name>
ENV AZURE_CONN_STR ""

ENV AZURE_CONTAINER_NAME ""
ENV AZURE_BLOB_NAME_STORE ""
ENV AZURE_BLOB_NAME_EXPORT ""

ENV HOST "localhost"
ENV PORT "8000"
ENV LOG_LEVEL "INFO"

COPY requirements.txt ./
RUN apk add gcc musl-dev libffi-dev && \
    apk add rust libxml2-dev libxslt-dev cargo openssl-dev && \
    pip3 install --no-cache-dir  -r requirements.txt && \
    apk del gcc cargo rust proj && \
    rm -rf /root/.cargo/

COPY src/ ./

CMD [ "python", "-u", "landeswasserstrassen.py"]
