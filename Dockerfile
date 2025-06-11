FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off
ENV ALEMBIC_CONFIG=/usr/src/app/alembic.ini

RUN apt update && apt install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
    dos2unix \
    && apt clean

RUN python -m pip install --upgrade pip && \
    pip install poetry

WORKDIR /usr/src/app
ENV PYTHONPATH=/usr/src/app:/usr/src/app/src

COPY pyproject.toml poetry.lock ./
COPY alembic.ini ./
COPY alembic ./alembic

RUN poetry config virtualenvs.create false
RUN poetry install --no-root --only main

COPY ./src ./src


COPY run.sh /usr/src/app/run.sh
RUN chmod +x /usr/src/app/run.sh

CMD ["/usr/src/app/run.sh"]
