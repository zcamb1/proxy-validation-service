# 🚀 DigitalOcean Deployment Script for Windows
# Usage: .\deploy.ps1 [app-platform|droplet]

param(
    [string]$DeploymentType = "app-platform"
)

Write-Host "🚀 Starting DigitalOcean deployment..." -ForegroundColor Green

# Check if doctl is installed
try {
    $null = Get-Command doctl -ErrorAction Stop
    Write-Host "✅ doctl found" -ForegroundColor Green
} catch {
    Write-Host "❌ doctl not found. Please install DigitalOcean CLI first:" -ForegroundColor Red
    Write-Host "   Windows: scoop install doctl" -ForegroundColor Yellow
    Write-Host "   Or download from: https://github.com/digitalocean/doctl/releases" -ForegroundColor Yellow
    exit 1
}

# Check if logged in
try {
    $null = doctl account get 2>$null
    Write-Host "✅ Logged in to DigitalOcean" -ForegroundColor Green
} catch {
    Write-Host "❌ Not logged in to DigitalOcean. Please run: doctl auth init" -ForegroundColor Red
    exit 1
}

if ($DeploymentType -eq "app-platform") {
    Write-Host "📦 Deploying to DigitalOcean App Platform..." -ForegroundColor Cyan
    
    # Create app spec
    $appSpec = @"
name: proxy-validation-service
services:
- name: proxy-service
  source_dir: .
  github:
    repo: your-username/your-repo
    branch: main
  run_command: gunicorn --bind 0.0.0.0:`$PORT --workers 1 --timeout 120 app:app
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
"@
    
    $appSpec | Out-File -FilePath "app.yaml" -Encoding UTF8
    
    # Deploy to App Platform
    doctl apps create --spec app.yaml
    
    Write-Host "✅ App Platform deployment initiated!" -ForegroundColor Green
    Write-Host "🔗 Check your DigitalOcean Console for the app URL" -ForegroundColor Yellow
    
} elseif ($DeploymentType -eq "droplet") {
    Write-Host "🖥️  Deploying to DigitalOcean Droplet..." -ForegroundColor Cyan
    
    # Create droplet
    $dropletName = "proxy-service-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    
    Write-Host "Creating droplet: $dropletName" -ForegroundColor Yellow
    
    # Get SSH key ID
    $sshKeyId = (doctl compute ssh-key list --format ID,Name --no-header | Select-Object -First 1).Split()[0]
    
    # Create droplet
    doctl compute droplet create $dropletName `
        --size s-1vcpu-1gb `
        --image ubuntu-22-04-x64 `
        --region sgp1 `
        --ssh-keys $sshKeyId
    
    Write-Host "⏳ Waiting for droplet to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Get droplet IP
    $dropletIp = (doctl compute droplet get $dropletName --format PublicIPv4 --no-header).Trim()
    Write-Host "🌐 Droplet IP: $dropletIp" -ForegroundColor Green
    
    Write-Host "📦 Manual deployment required:" -ForegroundColor Yellow
    Write-Host "1. SSH into droplet: ssh root@$dropletIp" -ForegroundColor Cyan
    Write-Host "2. Run these commands:" -ForegroundColor Cyan
    Write-Host @"
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install docker-compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-`$(uname -s)-`$(uname -m)" -o /usr/local/bin/docker-compose
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
"@ -ForegroundColor White
    
    Write-Host "✅ Droplet created successfully!" -ForegroundColor Green
    Write-Host "🌐 Access your app at: http://$dropletIp" -ForegroundColor Green
    
} else {
    Write-Host "❌ Invalid deployment type. Use: app-platform or droplet" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 Deployment process completed!" -ForegroundColor Green 