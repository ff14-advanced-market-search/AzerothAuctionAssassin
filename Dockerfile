# syntax=docker/dockerfile:1

# Alpine is chosen for its small footprint
# compared to Ubuntu

FROM python:3.13.0a6-slim

# install packages
RUN pip3 install tenacity requests PyQt5 \
    && apt-get update \
    && apt-get install -y libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# copy over files
WORKDIR /app
RUN mkdir /app/AzerothAuctionAssassinData/
RUN mkdir /app/utils/
COPY ./mega_alerts.py /app/
COPY ./utils/* /app/utils/
COPY ./AzerothAuctionAssassinData/* /app/AzerothAuctionAssassinData/
COPY ./run /app/
RUN chmod +x /app/*

# make default files
RUN printf "{}" > /app/AzerothAuctionAssassinData/desired_ilvl.json
RUN printf "[]" > /app/AzerothAuctionAssassinData/desired_ilvl_list.json
RUN printf "{}" > /app/AzerothAuctionAssassinData/desired_items.json
RUN printf "{}" > /app/AzerothAuctionAssassinData/desired_pets.json
RUN printf "{}" > /app/AzerothAuctionAssassinData/mega_data.json

CMD ["python3", "/app/mega_alerts.py"]