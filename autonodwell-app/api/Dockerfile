FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Quarter-acre land prices for `python -m app.load_land`.
COPY data ./data
RUN useradd -r app && chown -R app /srv
USER app
# Cloud Run sets $PORT. Migrations run as a separate Cloud Run Job (see deploy/), not on boot.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips="*"
