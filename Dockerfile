# 🏗 Build Stage
FROM python:3.10.0 as builder

WORKDIR /app

RUN python -m venv /app/venv

ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 🚀 App Stage
FROM python:3.10.0

RUN groupadd -g 999 python && useradd -r -u 999 -g python python
RUN mkdir /app && chown python:python /app

WORKDIR /app

COPY --chown=python:python --from=builder /app/venv ./venv
COPY --chown=python:python src /app/src
COPY --chown=python:python src/config.json /app/src/config.json
COPY --chown=python:python src/abi /app/src/abi
COPY --chown=python:python src/wallets.json /app/src/wallets.json

USER 999

ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH="${PYTHONPATH}:/app"

# 📌 Start Locust in standalone mode (for simple tests)
CMD ["locust", "-f", "src/performance_test.py"]
