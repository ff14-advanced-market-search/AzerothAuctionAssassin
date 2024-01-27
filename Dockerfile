# syntax=docker/dockerfile:1

# Alpine is chosen for its small footprint
# compared to Ubuntu

FROM python:slim-bookworm

RUN pip3 install tenacity requests PyQt5 \
    && apt-get update \
    && apt-get install -y libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app
RUN mkdir /app/AzerothAuctionAssassinData/
RUN mkdir /app/utils/
COPY ./mega_alerts.py /app/
COPY ./utils/* /app/utils/
COPY ./data/* /app/data/
COPY ./AzerothAuctionAssassinData/mega/* /app/AzerothAuctionAssassinData/
COPY ./run /app/
RUN chmod +x /app/*

CMD ["python3", "/app/mega_alerts.py"]