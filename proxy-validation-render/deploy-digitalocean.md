# 🚀 DigitalOcean Deployment Guide

## Phương pháp 1: DigitalOcean App Platform (Khuyến nghị)

### Bước 1: Chuẩn bị
1. Đăng ký tài khoản DigitalOcean
2. Cài đặt DigitalOcean CLI (doctl):
   ```bash
   # Windows
   scoop install doctl
   # hoặc
   choco install doctl
   ```

### Bước 2: Deploy lên App Platform
1. Đăng nhập vào DigitalOcean Console
2. Vào "Apps" → "Create App"
3. Connect với GitHub repository
4. Chọn branch và source directory: `proxy-validation-render`
5. Cấu hình:
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app`
   - **Port**: `8080`

### Bước 3: Environment Variables
Thêm các biến môi trường:
- `PORT`: `8080`
- `PYTHON_VERSION`: `3.9.16`

---

## Phương pháp 2: DigitalOcean Droplet với Docker

### Bước 1: Tạo Droplet
1. Tạo Droplet mới với Ubuntu 22.04
2. Chọn plan: Basic → $6/month (1GB RAM, 1 CPU)
3. Chọn datacenter gần nhất (Singapore)

### Bước 2: SSH vào Droplet
```bash
ssh root@your-droplet-ip
```

### Bước 3: Cài đặt Docker
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add user to docker group
usermod -aG docker $USER
```

### Bước 4: Deploy ứng dụng
```bash
# Clone repository
git clone https://github.com/your-username/your-repo.git
cd your-repo/proxy-validation-render

# Build và run Docker container
docker build -t proxy-service .
docker run -d -p 80:8080 --name proxy-app proxy-service

# Hoặc sử dụng docker-compose
docker-compose up -d
```

### Bước 5: Cấu hình Firewall
```bash
# Mở port 80 và 443
ufw allow 80
ufw allow 443
ufw enable
```

---

## Phương pháp 3: DigitalOcean App Platform với Dockerfile

### Bước 1: Sử dụng Dockerfile
1. App Platform sẽ tự động detect Dockerfile
2. Không cần cấu hình build/run command
3. Deploy trực tiếp từ repository

### Bước 2: Cấu hình
- **Source Directory**: `proxy-validation-render`
- **Port**: `8080`
- **Health Check Path**: `/api/health`

---

## Kiểm tra Deployment

### Test API endpoints:
```bash
# Health check
curl https://your-app-url/api/health

# Get proxy stats
curl https://your-app-url/api/ultra/stats

# Get alive proxies
curl https://your-app-url/api/proxy/alive?count=10
```

### Monitor logs:
```bash
# Nếu dùng Docker
docker logs proxy-app

# Nếu dùng App Platform
# Xem logs trong DigitalOcean Console
```

---

## Troubleshooting

### Lỗi thường gặp:
1. **Port binding error**: Kiểm tra PORT environment variable
2. **Memory issues**: Tăng RAM cho Droplet hoặc optimize code
3. **Timeout errors**: Tăng timeout trong gunicorn config

### Debug commands:
```bash
# Check container status
docker ps -a

# Check logs
docker logs proxy-app

# Restart service
docker restart proxy-app
```

---

## Cost Optimization

### App Platform:
- Basic: $5/month (512MB RAM, 0.25 CPU)
- Pro: $12/month (1GB RAM, 0.5 CPU)

### Droplet:
- Basic: $6/month (1GB RAM, 1 CPU)
- Regular: $12/month (2GB RAM, 1 CPU)

**Khuyến nghị**: Bắt đầu với App Platform Basic plan để test, sau đó upgrade nếu cần. 