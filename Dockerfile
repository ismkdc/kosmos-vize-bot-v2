FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir curl_cffi pycryptodome

COPY bot.py .

VOLUME ["/data"]

ENV TOKEN_FILE=/data/token.txt
ENV TZ=Europe/Istanbul

CMD ["python", "-u", "bot.py"]
