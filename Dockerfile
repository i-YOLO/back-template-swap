FROM python:3.12.4-alpine AS build

RUN pip install fastapi uvicorn httpx[cli,http2]
RUN pip install sqlalchemy psycopg2-binary pymysql asyncpg aiomysql
RUN pip install redis aio_pika python-jose pycryptodome colorama
RUN pip install async-lru xxhash base58
RUN pip install web3
RUN pip install starlette
RUN pip install pydantic
RUN pip install pandas
RUN pip install pyecharts
RUN pip install aiosqlite


FROM build AS deploy

WORKDIR /app

COPY . .