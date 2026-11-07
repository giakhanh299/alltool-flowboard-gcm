#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALLTOOL.PRO Marketplace Backend API (Port 8025)
Lightweight SQLite + HTTP JSON API (Zero external dependencies, runs on standard Python 3)
"""
import json
from task_manager import handle as handle_tasks
import os
import sqlite3
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path("/var/www/alltool.pro")
DB_PATH = BASE_DIR / "data" / "marketplace.db"
ADMIN_KEY = os.environ.get("ALLTOOL_ADMIN_KEY", "giakhanh2026")

SEED_TOOLS = [
    {
        "title": "Auto Render TikTok / Reels 9:16 Ultra-HD (OCR + AI Voice + MC Ảo)",
        "category": "Tool AI & Video",
        "platform": "Windows / Server / API",
        "price_display": "1.500.000đ / Vĩnh viễn",
        "license_type": "Mua vĩnh viễn + Kèm Source",
        "badge": "VERIFIED VIP",
        "is_vip": 1,
        "short_desc": "Tự động tải video Douyin/TikTok, xóa sạch chữ Trung/watermark bằng AI, dịch phụ đề #FFE866, lồng tiếng Việt tự nhiên & ghép MC dẫn chuyện chuẩn 9:16 iPhone.",
        "features": "Chuẩn hóa 1080x1920 60fps Lanczos4 Ultra-HD\nTự động cắt 12s cảnh gay cấn đưa lên mở đầu giữ chân người xem\nTẩy phụ đề gốc + phủ kính mờ Frosted Glass Pill độc quyền\nTự tạo Ảnh Bìa Poster 9:16 chữ 3D Full Bộ\nTích hợp duyệt và điều khiển qua Bot Telegram",
        "image_url": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=900&q=80",
        "demo_url": "https://t.me/GiaGiaKhanh",
        "seller_name": "Gia Khánh Studio (Admin)",
        "seller_zalo": "0772995862",
        "seller_telegram": "GiaGiaKhanh",
        "payment_info": "Liên hệ trực tiếp Zalo 0772995862 hoặc Telegram @GiaGiaKhanh để xem demo và cài đặt tận nơi.",
        "views": 342,
        "rating": 5.0,
    },
    {
        "title": "Multi-Topic Facebook Group Lead Scanner & Auto Bot Zalo",
        "category": "Tool Facebook",
        "platform": "Windows / Node.js / SQLite",
        "price_display": "800.000đ / Tháng",
        "license_type": "Thuê theo tháng / Vĩnh viễn",
        "badge": "BÁN CHẠY",
        "is_vip": 1,
        "short_desc": "Quét khách hàng tiềm năng (tìm nhà trọ, xe ghép, bất động sản, dịch vụ...) từ hàng trăm hội nhóm Facebook theo từ khóa thời gian thực, tự động bắn thông báo Zalo.",
        "features": "Quét đa luồng 24/7 không khóa nick\nBộ lọc AI phân loại đúng khách cần mua vs bài spam quảng cáo\nDashboard Web quản lý danh sách Lead + xuất Excel\nTự động đẩy tin nhắn báo khách mới qua Zalo / Telegram trong 3 giây",
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80",
        "demo_url": "https://zalo.me/0772995862",
        "seller_name": "Gia Khánh Studio (Admin)",
        "seller_zalo": "0772995862",
        "seller_telegram": "GiaGiaKhanh",
        "payment_info": "Hỗ trợ test thử 24h. Liên hệ Zalo 0772995862 hoặc Telegram @GiaGiaKhanh.",
        "views": 289,
        "rating": 5.0,
    },
    {
        "title": "Fanpage Control Center v2.0 — Hệ Thống Nuôi & Đăng Tự Động 100 Kênh",
        "category": "Tool Facebook",
        "platform": "Web Cloud + Windows Macro",
        "price_display": "2.500.000đ / Full Bộ",
        "license_type": "Bàn giao trọn gói",
        "badge": "VERIFIED VIP",
        "is_vip": 1,
        "short_desc": "Trung tâm điều hành hàng loạt Fanpage Reels & Video: tự động lên lịch giờ vàng, rải comment chéo chứa link, tự động dọn unfollow và báo cáo tăng trưởng.",
        "features": "Giao diện Web Command Center quản lý tập trung từ xa\nTự động đăng Reels + Video kèm ảnh bìa 9:16 theo khung giờ vàng\nTự động thả comment điều hướng và tương tác chéo an toàn\nTích hợp trợ lý AI kiểm tra chất lượng video (QC) tự động 15 phút/lần",
        "image_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80",
        "demo_url": "https://t.me/GiaGiaKhanh",
        "seller_name": "Gia Khánh Studio (Admin)",
        "seller_zalo": "0772995862",
        "seller_telegram": "GiaGiaKhanh",
        "payment_info": "Bảo hành trọn đời + hỗ trợ setup VPS riêng. Zalo: 0772995862 | Tele: @GiaGiaKhanh.",
        "views": 418,
        "rating": 5.0,
    },
    {
        "title": "News Autopilot 24H — Dựng Video Tin Tức & Bóng Đá Tự Động 100%",
        "category": "Tool AI & Video",
        "platform": "Windows / Python",
        "price_display": "1.200.000đ / Vĩnh viễn",
        "license_type": "Mua vĩnh viễn",
        "badge": "HOT",
        "is_vip": 0,
        "short_desc": "Tự động săn tin nóng bóng đá, công nghệ, đời sống 24h; viết lại kịch bản bằng AI, ghép chuyển động Ken Burns, giọng đọc truyền cảm và phụ đề chuẩn nhà đài.",
        "features": "Tự động cào tin mới nhất mỗi sáng và chiều\nAI biên tập lại văn phong cuốn hút, chống bản quyền\nRender video 9:16 và 16:9 tốc độ cao kèm nhạc nền tin tức\nTự động đẩy vào lịch đăng Fanpage mỗi ngày",
        "image_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=900&q=80",
        "demo_url": "https://zalo.me/0772995862",
        "seller_name": "Gia Khánh Studio (Admin)",
        "seller_zalo": "0772995862",
        "seller_telegram": "GiaGiaKhanh",
        "payment_info": "Liên hệ Zalo 0772995862 hoặc Telegram @GiaGiaKhanh.",
        "views": 195,
        "rating": 4.9,
    },
]


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            platform TEXT DEFAULT 'Windows / Web',
            price_display TEXT NOT NULL,
            license_type TEXT DEFAULT 'Mua vĩnh viễn',
            badge TEXT DEFAULT 'MỚI ĐĂNG',
            is_vip INTEGER DEFAULT 0,
            short_desc TEXT NOT NULL,
            features TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            demo_url TEXT DEFAULT '',
            seller_name TEXT NOT NULL,
            seller_zalo TEXT DEFAULT '',
            seller_telegram TEXT DEFAULT '',
            payment_info TEXT DEFAULT '',
            views INTEGER DEFAULT 1,
            rating REAL DEFAULT 5.0,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute("SELECT COUNT(*) FROM tools")
    cnt = cur.fetchone()[0]
    if cnt == 0:
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        for item in SEED_TOOLS:
            cur.execute(
                """
                INSERT INTO tools (
                    title, category, platform, price_display, license_type, badge, is_vip,
                    short_desc, features, image_url, demo_url, seller_name, seller_zalo,
                    seller_telegram, payment_info, views, rating, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["title"],
                    item["category"],
                    item["platform"],
                    item["price_display"],
                    item["license_type"],
                    item["badge"],
                    item["is_vip"],
                    item["short_desc"],
                    item["features"],
                    item["image_url"],
                    item["demo_url"],
                    item["seller_name"],
                    item["seller_zalo"],
                    item["seller_telegram"],
                    item["payment_info"],
                    item["views"],
                    item["rating"],
                    now_str,
                ),
            )
    conn.commit()
    conn.close()


def clean_str(val, max_len=1500):
    s = str(val or "").strip()
    return s[:max_len]


class MarketplaceHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        if handle_tasks(self):
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ("/api/health", "/api/v1/health"):
            self._send_json(200, {"status": "ok", "domain": "alltool.pro", "service": "marketplace"})
            return

        if path == "/api/tools":
            cat = clean_str(qs.get("category", [""])[0], 100)
            q = clean_str(qs.get("q", [""])[0], 120).lower()
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            sql = "SELECT * FROM tools WHERE 1=1"
            params = []
            if cat and cat != "all":
                sql += " AND category = ?"
                params.append(cat)
            if q:
                sql += " AND (LOWER(title) LIKE ? OR LOWER(short_desc) LIKE ? OR LOWER(features) LIKE ? OR LOWER(seller_name) LIKE ?)"
                like_q = f"%{q}%"
                params.extend([like_q, like_q, like_q, like_q])
            sql += " ORDER BY is_vip DESC, id DESC LIMIT 200"
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            self._send_json(
                200,
                {
                    "ok": True,
                    "count": len(rows),
                    "admin_contact": {
                        "name": "Admin Gia Khánh",
                        "zalo": "0772995862",
                        "zalo_url": "https://zalo.me/0772995862",
                        "telegram": "@GiaGiaKhanh",
                        "telegram_url": "https://t.me/GiaGiaKhanh",
                    },
                    "tools": rows,
                },
            )
            return

        self._send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self):
        if handle_tasks(self):
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(min(length, 2_000_000)) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8", errors="ignore") or "{}")
        except Exception:
            body = {}

        # 1. Đăng bán tool mới -> Duyệt ngay lập tức (Instant Publish)
        if path == "/api/tools":
            title = clean_str(body.get("title"), 160)
            category = clean_str(body.get("category") or "Tool MMO & Khác", 80)
            platform = clean_str(body.get("platform") or "Windows / Web", 80)
            price_display = clean_str(body.get("price_display"), 80)
            license_type = clean_str(body.get("license_type") or "Mua vĩnh viễn", 80)
            short_desc = clean_str(body.get("short_desc"), 600)
            features = clean_str(body.get("features"), 2000)
            image_url = clean_str(body.get("image_url"), 500)
            demo_url = clean_str(body.get("demo_url"), 500)
            seller_name = clean_str(body.get("seller_name"), 100)
            seller_zalo = clean_str(body.get("seller_zalo"), 50)
            seller_telegram = clean_str(body.get("seller_telegram"), 80).lstrip("@")
            payment_info = clean_str(body.get("payment_info"), 500)

            if not title or not price_display or not short_desc or not seller_name:
                self._send_json(
                    400,
                    {"ok": False, "error": "Vui lòng điền đủ Tên Tool, Giá bán, Mô tả ngắn và Tên người bán!"},
                )
                return
            if not seller_zalo and not seller_telegram:
                self._send_json(
                    400,
                    {"ok": False, "error": "Vui lòng nhập ít nhất 1 kênh liên hệ (Số Zalo hoặc Username Telegram)!"},
                )
                return

            if not image_url or not image_url.startswith("http"):
                image_url = "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=900&q=80"

            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO tools (
                    title, category, platform, price_display, license_type, badge, is_vip,
                    short_desc, features, image_url, demo_url, seller_name, seller_zalo,
                    seller_telegram, payment_info, views, rating, created_at
                ) VALUES (?, ?, ?, ?, ?, 'MỚI ĐĂNG', 0, ?, ?, ?, ?, ?, ?, ?, ?, 1, 5.0, ?)
                """,
                (
                    title,
                    category,
                    platform,
                    price_display,
                    license_type,
                    short_desc,
                    features,
                    image_url,
                    demo_url,
                    seller_name,
                    seller_zalo,
                    seller_telegram,
                    payment_info,
                    now_str,
                ),
            )
            new_id = cur.lastrowid
            conn.commit()
            conn.close()
            self._send_json(
                201,
                {
                    "ok": True,
                    "message": "Đăng bán Tool thành công! Tool của bạn đã hiển thị ngay trên trang chủ.",
                    "tool_id": new_id,
                },
            )
            return

        # 2. Tăng lượt xem khi khách bấm xem chi tiết tool
        if path.startswith("/api/tools/") and path.endswith("/view"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[2].isdigit():
                tid = int(parts[2])
                conn = sqlite3.connect(str(DB_PATH))
                conn.execute("UPDATE tools SET views = views + 1 WHERE id = ?", (tid,))
                conn.commit()
                conn.close()
                self._send_json(200, {"ok": True})
                return

        # 3. Quyền Admin: Ghim VIP hoặc Xóa bài
        if path == "/api/admin/action":
            req_key = self.headers.get("X-Admin-Key") or body.get("admin_key") or ""
            if req_key != ADMIN_KEY:
                self._send_json(403, {"ok": False, "error": "Sai mã bảo mật Admin!"})
                return
            action = body.get("action")
            tid = int(body.get("tool_id") or 0)
            conn = sqlite3.connect(str(DB_PATH))
            if action == "delete" and tid > 0:
                conn.execute("DELETE FROM tools WHERE id = ?", (tid,))
            elif action == "toggle_vip" and tid > 0:
                conn.execute(
                    "UPDATE tools SET is_vip = CASE WHEN is_vip=1 THEN 0 ELSE 1 END, badge = CASE WHEN is_vip=1 THEN 'ĐÃ KIỂM DUYỆT' ELSE 'VERIFIED VIP' END WHERE id = ?",
                    (tid,),
                )
            conn.commit()
            conn.close()
            self._send_json(200, {"ok": True})
            return

        self._send_json(404, {"ok": False, "error": "Endpoint not found"})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", 8025), MarketplaceHandler)
    print("ALLTOOL.PRO Marketplace API listening on 127.0.0.1:8025")
    server.serve_forever()
