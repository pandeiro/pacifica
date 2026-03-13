# Deployment Guide

This document describes how the Pacifica CI/CD pipeline works and how to set up the VPS.

## Architecture

The deployment uses **GitHub Actions** to build and push Docker images to **GitHub Container Registry (GHCR)**, then deploys to a VPS via SSH.

### Services

- **PostgreSQL**: Runs once via `docker-compose.base.yml`, shared between environments
- **API (Production)**: Runs on port 4900 (localhost only, accessed via nginx)
- **API (Staging)**: Runs on port 4901 (localhost only, accessed via nginx)
- **Scraper**: Runs periodically (not yet automated)

### File Structure on VPS

```
/opt/pacifica/
├── docker-compose.base.yml    # Postgres service
├── docker-compose.prod.yml    # Production API + scraper
├── docker-compose.staging.yml # Staging API + scraper (PRs)
├── migrations/                # Database migrations
└── seed/                      # Seed data
```

### Static Assets

- **Production**: `/var/www/pacifica/prod/` → served at https://pch.onl
- **Staging**: `/var/www/pacifica/staging/` → served at https://staging.pch.onl

## GitHub Secrets Required

Set these via the GitHub CLI:

```bash
gh secret set DEPLOY_KEY < ~/.ssh/your_deploy_key
gh secret set DEPLOY_HOST --body "pch.onl"
gh secret set DEPLOY_USER --body "deploy"
gh secret set DEPLOY_SERVICES_PATH --body "/opt/pacifica"
gh secret set DEPLOY_STATIC_PATH_PROD --body "/var/www/pacifica/prod"
gh secret set DEPLOY_STATIC_PATH_STAGING --body "/var/www/pacifica/staging"
gh secret set POSTGRES_PASSWORD --body "your_secure_password"
```

## VPS Setup (One-time)

1. **Create deploy user**:
```bash
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy
```

2. **Add deploy key to authorized_keys**:
```bash
sudo mkdir -p /home/deploy/.ssh
sudo echo "YOUR_PUBLIC_KEY" > /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

3. **Create directories**:
```bash
sudo mkdir -p /opt/pacifica
sudo mkdir -p /var/www/pacifica/prod
sudo mkdir -p /var/www/pacifica/staging
sudo chown -R deploy:deploy /opt/pacifica
sudo chown -R deploy:deploy /var/www/pacifica
```

4. **Initial database setup**:
```bash
cd /opt/pacifica
docker compose -f docker-compose.base.yml up -d
# Run migrations manually first time
docker compose -f docker-compose.base.yml exec postgres psql -U pacifica -d pacifica -f /migrations/001_tables.sql
```

## Nginx Configuration

Example nginx config for the VPS:

```nginx
# /etc/nginx/sites-available/pch.onl
server {
    listen 443 ssl http2;
    server_name pch.onl;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Static assets
    location / {
        root /var/www/pacifica/prod;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:4900/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Staging
server {
    listen 443 ssl http2;
    server_name staging.pch.onl;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        root /var/www/pacifica/staging;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:4901/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Manual Deployment (if needed)

If GitHub Actions is unavailable, you can deploy manually:

```bash
# On VPS as deploy user
cd /opt/pacifica

# Pull latest images
docker compose -f docker-compose.base.yml -f docker-compose.prod.yml pull

# Restart services
docker compose -f docker-compose.base.yml -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.base.yml -f docker-compose.prod.yml ps
```