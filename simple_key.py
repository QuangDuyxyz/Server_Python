"""
Tạo key đơn giản cho thiết bị
"""
from fastapi import FastAPI, HTTPException
import random
import string
import mysql.connector
import os
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

app = FastAPI(title="Simple Key Generator")

# Cấu hình CORS
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả nguồn gốc
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình kết nối database
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3308")),
    "user": os.getenv("DB_USER", "KingAutoColony"),
    "password": os.getenv("DB_PASSWORD", "StrongPass123"),
    "database": os.getenv("DB_NAME", "license_system"),
}

def generate_key():
    """Tạo key ngẫu nhiên 16 ký tự"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(16))

@app.get("/generate-key/{device_id}")
async def create_key(device_id: int):
    """Tạo key cho thiết bị với ID cụ thể"""
    try:
        # Kết nối đến MySQL
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Kiểm tra thiết bị tồn tại
        cursor.execute("SELECT * FROM devices WHERE id = %s", (device_id,))
        device = cursor.fetchone()
        
        if not device:
            raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
        
        # Tạo key và cập nhật
        key = generate_key()
        cursor.execute(
            "UPDATE devices SET key_code = %s, expires_at = DATE_ADD(NOW(), INTERVAL 1 YEAR) WHERE id = %s",
            (key, device_id)
        )
        connection.commit()
        
        # Thêm log
        cursor.execute(
            "INSERT INTO logs (mac, hostname, action, performed_by, timestamp) VALUES (%s, %s, %s, %s, NOW())",
            (device['mac'], device['hostname'], 'generate_key', 1)
        )
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return {
            "success": True,
            "device_id": device_id,
            "key": key,
            "message": "Key được tạo thành công!"
        }
        
    except mysql.connector.Error as err:
        return {
            "success": False,
            "error": f"Lỗi MySQL: {err}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Lỗi: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3002)
