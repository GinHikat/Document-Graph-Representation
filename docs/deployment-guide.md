# Deployment Guide

## Prerequisites

- Docker & Docker Compose
- Neo4j AuraDB or local Neo4j
- AWS S3 bucket (for documents)
- Domain with SSL (production)

## Local Development

### Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirement.txt
pip install -r requirements-api.txt

# Configure environment
cp .env.example .env
# Edit .env with credentials

# Run server
cd api
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Docker Deployment

### Dockerfile (Backend)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirement.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirement.txt -r requirements-api.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile (Frontend)

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - neo4j

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

  neo4j:
    image: neo4j:5.27.0
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

## Production Deployment

### Environment Variables

```bash
# Backend
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<secure-password>
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_BUCKET_NAME=<bucket>
AWS_REGION=ap-southeast-1

# Frontend (build-time)
VITE_API_URL=https://api.yourdomain.com
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Cloud Deployment Options

### AWS

1. **ECS/Fargate** for containers
2. **RDS** for PostgreSQL (if needed)
3. **S3** for documents
4. **CloudFront** for frontend CDN
5. **Route53** for DNS

### Google Cloud

1. **Cloud Run** for containers
2. **Cloud Storage** for documents
3. **Cloud CDN** for frontend

### Railway/Render

Simple deployment:
```bash
# Backend: Connect repo, set env vars
# Frontend: Connect repo, build command: npm run build
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Neo4j connection
curl http://localhost:8000/api/graph/stats
```

### Logging

Configure structured logging:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Backup

### Neo4j Backup

```bash
# AuraDB: Use built-in backup
# Self-hosted:
neo4j-admin database dump neo4j --to-path=/backups/
```

### S3 Backup

Enable versioning on S3 bucket for document history.
