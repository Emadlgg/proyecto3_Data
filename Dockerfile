FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Por defecto solo las dependencias del dashboard/ETL (imagen ligera).
# Para el pipeline MLOps: docker compose build --build-arg REQS=requirements.txt
ARG REQS=requirements-app.txt
COPY requirements.txt requirements-app.txt ./
RUN pip install --no-cache-dir -r ${REQS}

COPY .streamlit ./.streamlit
COPY app.py ./
COPY pages ./pages
COPY src ./src
COPY config ./config
# Directorios que se montan como volúmenes (los datos NUNCA se copian a la imagen).
RUN mkdir -p data/raw data/processed docs artifacts

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4).status==200 else 1)"

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
