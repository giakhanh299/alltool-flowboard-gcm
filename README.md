# ALLTOOL.PRO & GCM.ALLTOOL.PRO (FlowBoard Enterprise v3)

Repository đồng bộ mã nguồn chính thức đang chạy trên máy chủ VPS (`163.128.42.185`) cho:
1. **Chợ Tool**: `https://alltool.pro`
2. **FlowBoard Quản Lý Công Việc & Sản Xuất (GCM)**: `https://gcm.alltool.pro`

---

## 1. Cấu trúc thư mục trên VPS (`/var/www/alltool.pro`)

```text
/var/www/alltool.pro/
├── html/
│   ├── index.html                  # Giao diện trang chủ Chợ Tool (alltool.pro)
│   └── cong-viec/                  # Web root của https://gcm.alltool.pro
│       ├── index.html              # Trang đăng nhập & khung ứng dụng FlowBoard
│       ├── auth.js                 # Xác thực phiên làm việc & đổi mật khẩu
│       ├── flowboard.js            # Logic chính FlowBoard v3 + Thống kê dự án + Nhân sự
│       ├── flowboard.css           # Giao diện bảng công việc FlowBoard
│       └── style.css               # Giao diện màn hình đăng nhập
├── marketplace_server.py           # HTTP Server chính (cổng 127.0.0.1:8025)
├── task_manager.py                 # API xử lý /api/tasks/* (đăng nhập, lưu state, tải file <= 35MB)
├── flowboard_integrations.py       # API đồng bộ tích hợp HMAC (/api/tasks/integration)
├── import_projects_20261106.py     # Script nạp hồ sơ 15 dự án xưởng & nhân sự
├── test_integrations.py            # Bộ kiểm thử tự động tích hợp HMAC & chunk upload
├── data/                           # (Ignored trong Git) Chứa tasks.db, marketplace.db, tasks_auth.json
└── backup/                         # (Ignored trong Git) Chứa các bản sao lưu tự động hằng ngày
```

---

## 2. Nhật ký Cải tiến & Tối ưu hệ thống (Cập nhật ngày 07/11/2026)

1. **Dọn sạch dữ liệu test mẫu khỏi `data/tasks.db`**:
   - Đã loại bỏ dự án test (`prj1` - *Dự án Mẫu FlowBoard GCM*), nhân sự test (`p1` - *Admin FlowBoard*), công việc test (`t1`) và tệp rác (`doc_upload_test_123`).
   - Giữ nguyên vẹn **15 dự án thực tế của xưởng** (`GCM-HN`, `GCM-HG`, `GCM-CP`, ...) và **4 nhân sự thực tế** (`Phạm Văn Liền`, `Huỳnh Đức Nhân`, `Nguyễn Đức Vũ`, `Phùng Ngọc Quế`) cùng tệp báo cáo `REPORT-20261106`.
2. **Sửa tên file khi bấm nút "Tải Excel thống kê" (`html/cong-viec/flowboard.js`)**:
   - Trước đây khi bấm nút `Tải Excel thống kê` (`data-download-file="REPORT-20261106"`), trình duyệt lưu file tên là `tep` (thiếu đuôi `.xlsx`).
   - Đã cập nhật hàm `downloadFile(id)` trong `flowboard.js` để tự động đặt tên chuẩn: **`Thong-ke-du-an-GCM-2026-11-06.xlsx`**.
3. **Tối ưu Nginx & Bảo mật cho `https://gcm.alltool.pro`**:
   - Bật nén `gzip` (level 6) cho `text/css`, `application/javascript`, `application/json`, `image/svg+xml` giúp tốc độ tải trên di động/4G nhanh gấp 3–4 lần.
   - Bổ sung Security Headers (`Strict-Transport-Security`, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`) và `Cache-Control: no-cache` cho `.js/.css/.html` để trình duyệt luôn nhận code mới nhất ngay khi cập nhật.
   - Giới hạn tải tệp đính kèm: `client_max_body_size 35m;`.
4. **Sao lưu tự động hằng ngày (`Cron + SQLite Online Backup`)**:
   - Script `/usr/local/bin/backup_alltool_gcm.sh` chạy tự động lúc `03:15` sáng mỗi ngày qua `/etc/cron.d/alltool-gcm-backup`.
   - Sử dụng `sqlite3.Connection.backup()` sao lưu an toàn cả `tasks.db` và `marketplace.db` sang `/var/www/alltool.pro/backup/` và tự động giữ lại 14 ngày gần nhất.

---

## 3. Lệnh vận hành dành cho Developer (`alltool_dev`)

- **Kiểm tra trạng thái dịch vụ Backend**:
  ```bash
  sudo systemctl status alltool-marketplace.service
  ```
- **Khởi động lại Backend sau khi sửa file `.py`**:
  ```bash
  sudo systemctl restart alltool-marketplace.service
  ```
- **Chạy bộ test tích hợp**:
  ```bash
  cd /var/www/alltool.pro && python3 test_integrations.py
  ```
