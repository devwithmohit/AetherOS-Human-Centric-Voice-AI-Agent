FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi==0.109.0 uvicorn[standard]==0.27.0
RUN echo "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    return {'status': 'healthy', 'service': 'function-executor'}\n@app.get('/')\ndef root():\n    return {'message': 'Function Executor Service'}" > main.py
EXPOSE 8007
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD curl -f http://localhost:8007/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"]
