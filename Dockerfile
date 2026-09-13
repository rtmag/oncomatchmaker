FROM node:22-slim AS web-build

WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml ./
COPY app/ app/
COPY schemas/ schemas/
COPY ingestion/ ingestion/
COPY normalization/ normalization/
COPY trials/ trials/
COPY evidence/ evidence/
COPY ui/ ui/
COPY tests/fixtures/ tests/fixtures/
COPY --from=web-build /build/web/dist web/dist/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
