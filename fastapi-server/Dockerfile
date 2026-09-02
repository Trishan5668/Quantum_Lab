FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# LLM provider defaults. Override at run time with `docker run -e ...`.
# - LLM_PROVIDER: "gemini" (default) or "local"
# - GEMINI_API_KEY: required when LLM_PROVIDER=gemini
# Leaving GEMINI_API_KEY unset is safe -- the server will auto-fallback
# to the offline `local` provider so /explain still works.
ENV LLM_PROVIDER=gemini \
    GEMINI_API_KEY=""

WORKDIR /srv

COPY ../quantum-simulator-core /srv/quantum-simulator-core
COPY . /srv/fastapi-server

RUN pip install -e /srv/quantum-simulator-core \
 && pip install -e /srv/fastapi-server \
 && python -c "import qiskit; import pennylane; from qdk import qsharp; qsharp.init(); print('editor runtimes ok')"

EXPOSE 8765

WORKDIR /srv/fastapi-server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
