FROM python:3.12-slim
WORKDIR /app
COPY packages/abhaysetu_protocol /tmp/protocol
RUN pip install /tmp/protocol
COPY hub/requirements.txt /tmp/requirements.txt
RUN grep -v "abhaysetu_protocol" /tmp/requirements.txt > /tmp/req.txt && pip install -r /tmp/req.txt
COPY hub /app
RUN mkdir -p /app/data
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
