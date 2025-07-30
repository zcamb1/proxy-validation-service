# 🚀 Quick Deploy to DigitalOcean

## Cách 1: App Platform (Đơn giản nhất)

### Bước 1: Chuẩn bị
```bash
# Cài đặt DigitalOcean CLI
scoop install doctl  # Windows
# hoặc
brew install doctl   # macOS

# Đăng nhập
doctl auth init
```

### Bước 2: Deploy
```bash
# Chạy script deploy
.\deploy.ps1 app-platform
```

## Cách 2: Droplet với Docker

### Bước 1: Tạo Droplet
```bash
.\deploy.ps1 droplet
```

### Bước 2: SSH vào Droplet và deploy
```bash
# SSH vào droplet (IP sẽ hiển thị sau khi tạo)
ssh root@your-droplet-ip

# Chạy các lệnh deploy
apt update && apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone repo và deploy
git clone https://github.com/your-username/your-repo.git
cd your-repo/proxy-validation-render
docker-compose up -d

# Mở firewall
ufw allow 80
ufw allow 443
ufw --force enable
```

## Cách 3: Manual qua Console

1. Đăng nhập vào [DigitalOcean Console](https://cloud.digitalocean.com/)
2. Vào "Apps" → "Create App"
3. Connect GitHub repository
4. Chọn source directory: `proxy-validation-render`
5. Cấu hình:
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app`
   - **Port**: `8080`

## Test API

Sau khi deploy thành công, test các endpoint:

```bash
# Health check
curl https://your-app-url/api/health

# Get proxy stats
curl https://your-app-url/api/ultra/stats

# Get alive proxies
curl https://your-app-url/api/proxy/alive?count=10
```

## Chi phí

- **App Platform Basic**: $5/tháng (512MB RAM)
- **Droplet Basic**: $6/tháng (1GB RAM)

## Troubleshooting

### Lỗi thường gặp:
1. **Port binding**: Kiểm tra PORT=8080
2. **Memory issues**: Upgrade plan
3. **Timeout**: Tăng timeout trong gunicorn

### Debug:
```bash
# Check logs
docker logs proxy-app

# Restart service
docker restart proxy-app
``` 