FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY entrypoint.sh ./
COPY run_migrations.sh ./run_migrations.sh
RUN chmod +x ./entrypoint.sh || true
RUN chmod +x ./run_migrations.sh || true

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
