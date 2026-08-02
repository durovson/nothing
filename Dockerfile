FROM python:3.14.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . ./

# Reject unresolved merge markers and any other Python syntax error during
# the build, before Render starts replacing the currently healthy instance.
RUN python -m compileall -q app
RUN python -c "import app.main"

RUN addgroup --system app && adduser --system --ingroup app app
USER app

CMD ["python", "-m", "app.main"]
