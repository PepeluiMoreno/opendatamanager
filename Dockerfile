# Dockerfile para la app Python
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Navegador para la especie Headless (HeadlessFetcher / Playwright)
RUN python -m playwright install --with-deps chromium
COPY . .
COPY docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ARG BUILD_SHA=dev
ENV APP_VERSION=${BUILD_SHA}
ENTRYPOINT ["/entrypoint.sh"]