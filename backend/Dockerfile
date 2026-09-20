FROM python:3.12-slim
WORKDIR /app
COPY packages/abhaysetu_protocol /tmp/protocol
RUN pip install /tmp/protocol
COPY backend/requirements.txt /tmp/requirements.txt
RUN grep -v "abhaysetu_protocol" /tmp/requirements.txt > /tmp/req.txt && pip install -r /tmp/req.txt
COPY backend /app
ENV PYTHONPATH=/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
