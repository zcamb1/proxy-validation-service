#!/bin/bash

# 🚀 DigitalOcean Deployment Script
# Usage: ./deploy.sh [app-platform|droplet]

set -e

echo "🚀 Starting DigitalOcean deployment..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl not found. Please install DigitalOcean CLI first:"
    echo "   Windows: scoop install doctl"
    echo "   macOS: brew install doctl"
    echo "   Linux: snap install doctl"
    exit 1
fi

# Check if logged in
if ! doctl account get &> /dev/null; then
    echo "❌ Not logged in to DigitalOcean. Please run: doctl auth init"
    exit 1
fi

DEPLOYMENT_TYPE=${1:-app-platform}

if [ "$DEPLOYMENT_TYPE" = "app-platform" ]; then
    echo "📦 Deploying to DigitalOcean App Platform..."
    
    # Create app spec
    cat > app.yaml << EOF
name: proxy-validation-service
services:
- name: proxy-service
  source_dir: .
  github:
    repo: your-username/your-repo
    branch: main
  run_command: gunicorn --bind 0.0.0.0:\$PORT --workers 1 --timeout 120 app:app
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  health_check:
    http_path: /api/health
  envs:
  - key: PORT
    value: "8080"
  - key: PYTHON_VERSION
    value: "3.9.16"
EOF

    # Deploy to App Platform
    doctl apps create --spec app.yaml
    
    echo "✅ App Platform deployment initiated!"
    echo "🔗 Check your DigitalOcean Console for the app URL"
    
elif [ "$DEPLOYMENT_TYPE" = "droplet" ]; then
    echo "🖥️  Deploying to DigitalOcean Droplet..."
    
    # Create droplet
    DROPLET_NAME="proxy-service-$(date +%s)"
    
    echo "Creating droplet: $DROPLET_NAME"
    doctl compute droplet create $DROPLET_NAME \
        --size s-1vcpu-1gb \
        --image ubuntu-22-04-x64 \
        --region sgp1 \
        --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -1)
    
    echo "⏳ Waiting for droplet to be ready..."
    sleep 30
    
    # Get droplet IP
    DROPLET_IP=$(doctl compute droplet get $DROPLET_NAME --format PublicIPv4 --no-header)
    echo "🌐 Droplet IP: $DROPLET_IP"
    
    # Wait for SSH to be available
    echo "⏳ Waiting for SSH..."
    while ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$DROPLET_IP exit 2>/dev/null; do
        sleep 5
    done
    
    # Deploy application
    echo "📦 Deploying application..."
    ssh -o StrictHostKeyChecking=no root@$DROPLET_IP << 'EOF'
        # Update system
        apt update && apt upgrade -y
        
        # Install Docker
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        
        # Install docker-compose
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        
        # Clone repository (replace with your repo)
        git clone https://github.com/your-username/your-repo.git
        cd your-repo/proxy-validation-render
        
        # Build and run
        docker-compose up -d
        
        # Configure firewall
        ufw allow 80
        ufw allow 443
        ufw --force enable
EOF
    
    echo "✅ Droplet deployment completed!"
    echo "🌐 Access your app at: http://$DROPLET_IP"
    
else
    echo "❌ Invalid deployment type. Use: app-platform or droplet"
    exit 1
fi

echo "🎉 Deployment completed successfully!" 