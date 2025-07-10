# 🚀 Proxy Validation Service for Render

Service tự động kiểm tra proxy sống mỗi 5 phút và cung cấp API để ElevenLabs Tool sử dụng.

## ✨ Tính năng

- 🔄 Tự động fetch proxy từ 8 nguồn khác nhau mỗi 5 phút
- ⚡ Multi-threading validation với 30 workers
- 📊 Real-time API endpoints
- 🎯 Sort proxy theo tốc độ (nhanh nhất trước)
- 🌐 Web interface với live stats
- 🛡️ Error handling và fallback

## 🌍 Nguồn Proxy

Service tự động lấy proxy từ 8 nguồn:
- Server Alpha: proxifly/free-proxy-list
- Server Beta: TheSpeedX/PROXY-List
- Server Gamma: monosans/proxy-list
- Server Delta: hookzof/socks5_list
- Server Echo: proxyscrape.com API
- Server Foxtrot: proxy-list.download API
- Server Golf: clarketm/proxy-list
- Server Hotel: sunny9577/proxy-scraper

## 📡 API Endpoints

### GET `/api/proxy/alive`
Lấy danh sách proxy sống
- Params: `count` (số lượng, default: 50)
- Example: `/api/proxy/alive?count=100`

```json
{
  "success": true,
  "total_available": 234,
  "returned_count": 50,
  "proxies": [
    {
      "host": "1.2.3.4",
      "port": 8080,
      "type": "http",
      "speed": 1.23,
      "status": "alive",
      "ip": "1.2.3.4",
      "proxy_string": "1.2.3.4:8080"
    }
  ],
  "last_update": "2024-01-01T12:00:00",
  "sources_count": 8
}
```

### GET `/api/proxy/stats`
Thống kê proxy hiện có

```json
{
  "success": true,
  "alive_count": 234,
  "total_checked": 1000,
  "last_update": "2024-01-01T12:00:00",
  "cache_age_minutes": 3,
  "sources_count": 8,
  "service_status": "running"
}
```

## 🚀 Deploy lên Render

### 1. Tạo Repository GitHub

```bash
# Tạo repository mới trên GitHub
# Clone về máy
git clone https://github.com/your-username/proxy-validation-service.git
cd proxy-validation-service

# Copy files vào
cp -r proxy-validation-render/* .

# Push lên GitHub
git add .
git commit -m "Initial proxy validation service"
git push origin main
```

### 2. Deploy trên Render

1. Truy cập [Render.com](https://render.com)
2. Đăng nhập và click **"New +"**
3. Chọn **"Web Service"**
4. Connect GitHub repository vừa tạo
5. Cấu hình:
   - **Name**: `proxy-validation-service`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: `Free`

### 3. Lấy URL Service

Sau khi deploy thành công, bạn sẽ có URL như:
```
https://proxy-validation-service-xxxx.onrender.com
```

## 🔧 Tích hợp với ElevenLabs Tool

1. Mở file `config.ini` trong tool
2. Tìm section `[RENDER_SERVICE]`
3. Cập nhật URL:

```ini
[RENDER_SERVICE]
enabled = true
url = https://proxy-validation-service-xxxx.onrender.com
proxy_count = 50
timeout = 10
fallback_to_db = true
```

4. Restart tool và test button "lấy proxy sống"

## 📊 Monitoring

- Web interface: `https://your-service.onrender.com`
- Live stats: `https://your-service.onrender.com/api/proxy/stats`
- Render logs: Dashboard → Service → Logs

## 🔧 Troubleshooting

### Service không start
- Check Render logs
- Verify requirements.txt
- Check gunicorn command

### Không có proxy
- Check proxy sources (có thể bị block)
- Verify internet connection
- Check logs cho error messages

### Tool không connect được
- Verify URL trong config.ini
- Check network/firewall
- Test manual: `curl https://your-service.onrender.com/api/proxy/stats`

## 💡 Tips

- Service sẽ sleep sau 15 phút không activity (Render free plan)
- First request sau sleep sẽ mất 30-60s để wake up
- Service tự động check proxy mỗi 5 phút
- Proxy được sort theo tốc độ (nhanh nhất trước)

## 🎯 Performance

- Initial load: 200 proxy
- Refresh cycle: 400 proxy (mỗi 5 phút)
- Validation workers: 30 concurrent
- Response time: < 1s (khi service đã wake)

Perfect cho việc cung cấp proxy sống cho ElevenLabs Tool! 🚀 