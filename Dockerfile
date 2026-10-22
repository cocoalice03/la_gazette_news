ARG AIRFLOW_VERSION=3.2.2

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS build
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY pyproject.toml ./
COPY src ./src
RUN pip install .

FROM build AS test
RUN pip install ".[dev]"
COPY sources.csv ./
COPY dags ./dags
COPY tests ./tests
CMD ["sh", "-c", "ruff check . && ruff format --check . && pytest"]

FROM base AS runtime
RUN useradd --create-home --uid 10001 gazette \
    && mkdir -p /app/data \
    && chown gazette:gazette /app/data
COPY --from=build /opt/venv /opt/venv
COPY sources.csv ./
ENV PATH=/opt/venv/bin:$PATH
USER gazette
ENTRYPOINT ["python", "-m", "gazette.collecteur"]

FROM apache/airflow:${AIRFLOW_VERSION}-python3.12 AS airflow
ARG AIRFLOW_VERSION
COPY --chown=airflow:0 pyproject.toml /opt/gazette/
COPY --chown=airflow:0 src /opt/gazette/src
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" /opt/gazette
COPY --chown=airflow:0 sources.csv /opt/gazette/
COPY --chown=airflow:0 dags /opt/airflow/dags
