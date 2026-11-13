FROM python:3.12-slim
WORKDIR /app
ARG SOURCE_COMMIT=unknown
ENV SOURCE_COMMIT=$SOURCE_COMMIT
COPY requirements-runtime.lock .
RUN pip install --no-cache-dir -r requirements-runtime.lock
COPY . .
RUN useradd -m app && mkdir -p data && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
