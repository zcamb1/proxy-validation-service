# 🚀 Hướng dẫn Deploy nhanh

## 1. Tạo Repository GitHub

1. Truy cập https://github.com/new
2. Repository name: `proxy-validation-service`
3. Chọn `Public` 
4. Nhấn **Create repository**

## 2. Upload Files lên GitHub

### Cách 1: Drag & Drop (Dễ nhất)

1. Vào repository vừa tạo
2. Nhấn **uploading an existing file**
3. Drag & drop tất cả files trong folder `proxy-validation-render`:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `.gitignore`
4. Commit message: `Initial proxy validation service`
5. Nhấn **Commit changes**

### Cách 2: Git Commands

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/proxy-validation-service.git
cd proxy-validation-service

# Copy files
cp -r proxy-validation-render/* .

# Push lên GitHub
git add .
git commit -m "Initial proxy validation service"
git push origin main
```

## 3. Deploy lên Render

1. Truy cập https://render.com
2. Đăng nhập (có thể dùng GitHub account)
3. Nhấn **New +** → **Web Service**
4. Connect repository `proxy-validation-service` 

### Cấu hình Deploy:

```
Name: proxy-validation-service
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
Instance Type: Free
```

5. Nhấn **Create Web Service**
6. Đợi 3-5 phút để deploy

## 4. Lấy URL và Test

1. Sau khi deploy xong, copy URL (VD: `https://proxy-validation-service-xxxx.onrender.com`)
2. Test bằng cách truy cập URL → phải thấy trang web với thống kê
3. Test API: `https://your-url.onrender.com/api/proxy/stats`

## 5. Cấu hình Tool

1. Mở `config.ini` trong ElevenLabs Tool
2. Tìm section `[RENDER_SERVICE]`
3. Sửa URL:

```ini
[RENDER_SERVICE]
enabled = true
url = https://proxy-validation-service-xxxx.onrender.com
proxy_count = 50
timeout = 10
fallback_to_db = true
```

4. Restart tool và test button "lấy proxy sống"

## ✅ Xong!

Service sẽ tự động:
- Fetch proxy từ 8 nguồn mỗi 5 phút
- Validate và sort theo tốc độ
- Cung cấp API cho tool sử dụng

**First request có thể mất 30-60s** vì service cần wake up (free plan).

## 🆘 Nếu có lỗi:

1. Check Render logs: Dashboard → Service → Logs
2. Verify files đã upload đúng
3. Test manual: `curl https://your-url.onrender.com/api/proxy/alive`

Chúc deploy thành công! 🎉 