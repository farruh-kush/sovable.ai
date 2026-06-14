# Cloud Dev (Staging) Deployment Guide

This guide outlines how to deploy the AI Routing Layer to a single-node cloud Virtual Machine (VM) using Docker Compose. This environment is ideal for staging, QA, or internal team usage before moving to a full Kubernetes production cluster.

**Author:** Farruh

## Overview

**Use-case:** A team needs a shared, continuously running staging environment accessible via the internet to test integrations with their frontend applications.
**Pain point:** Setting up a full Kubernetes cluster for a staging environment is often overkill, expensive, and requires significant DevOps overhead.
**Solution:** Deploying the exact same Docker Compose stack used locally onto a single cloud VM (e.g., AWS EC2, DigitalOcean Droplet, Hetzner) behind an Nginx reverse proxy with SSL termination.

---

## Prerequisites

1. A Cloud VM running **Ubuntu 22.04 LTS or 24.04 LTS**.
   - Recommended specs: 2 vCPUs, 4GB RAM (minimum), 20GB SSD.
2. A domain name (e.g., `api-staging.yourdomain.com`) pointing to the VM's public IP address.
3. SSH access to the VM.

## Step 1: Provision the Server

SSH into your cloud VM and update the system packages:

```bash
sudo apt update && sudo apt upgrade -y
```

Install Docker and Docker Compose plugin:

```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
```

## Step 2: Clone and Configure

1. Clone the repository into `/opt`:
   ```bash
   cd /opt
   sudo git clone https://github.com/k-farruh/ai-routing-platform.git
   cd ai-routing-platform
   ```

2. Set up the environment variables:
   ```bash
   sudo cp .env.example .env
   sudo nano .env
   ```

3. **CRITICAL:** In the `.env` file, change the following values from their defaults:
   - `APP_ENV=staging`
   - `ADMIN_API_KEY=` (Generate a strong random string)
   - `SECRET_KEY=` (Generate a strong random string)
   - `POSTGRES_PASSWORD=` (Generate a strong random string)
   - `GRAFANA_PASSWORD=` (Set a secure password)
   - Add your actual LLM Provider API Keys.

## Step 3: Start the Platform

Run Docker Compose in detached mode:

```bash
sudo docker compose up --build -d
```

Verify that all containers are running:

```bash
sudo docker compose ps
```

## Step 4: Setup Nginx Reverse Proxy & SSL

To securely expose the Gateway service to the internet, we will use Nginx and Let's Encrypt (Certbot).

1. Install Nginx and Certbot:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   ```

2. Create an Nginx configuration file:
   ```bash
   sudo nano /etc/nginx/sites-available/ai-routing
   ```

3. Add the following configuration (replace `api-staging.yourdomain.com` with your actual domain):
   ```nginx
   server {
       listen 80;
       server_name api-staging.yourdomain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Required for SSE (Streaming)
           proxy_buffering off;
           proxy_cache off;
           proxy_read_timeout 86400s;
           proxy_send_timeout 86400s;
       }
   }
   ```

4. Enable the site and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/ai-routing /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

5. Obtain an SSL Certificate:
   ```bash
   sudo certbot --nginx -d api-staging.yourdomain.com
   ```
   *Follow the prompts to configure HTTPS redirection.*

## Step 5: Verify the Deployment

From your local machine, test the live staging endpoint using the `ADMIN_API_KEY` you configured in Step 2 to create a standard API key:

```bash
curl -X POST https://api-staging.yourdomain.com/v1/keys \
  -H "X-Admin-Key: <YOUR_SECURE_ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Staging Frontend Key",
    "tier": "pro"
  }'
```

Your cloud staging environment is now live and secure!

## Updating the Environment

When you push new code to the `master` branch, you can update the staging environment by running:

```bash
cd /opt/ai-routing-platform
sudo git pull origin master
sudo docker compose up --build -d
```
