from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import os
import datetime
import mysql.connector
from mysql.connector import Error
import random
from dotenv import load_dotenv
import json
import uvicorn

# Tải biến môi trường từ file .env
load_dotenv()

app = FastAPI(title="Key Management Colony API")

# Cấu hình CORS - cho phép các nguồn gốc khác truy cập API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:5174",
        "https://key-colony-auto.vercel.app",
        "https://key-management-colony.vercel.app",
        "https://key-colony-auto-quangduyxyz.vercel.app"
    ,
        "https://f44e-27-74-243-28.ngrok-free.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# OPTIONS route for CORS preflight requests
@app.options("/{path:path}")
async def options_route(path: str):
    return {"status": "OK"}
# Cấu hình kết nối database
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3308")),
    "user": os.getenv("DB_USER", "KingAutoColony"),
    "password": os.getenv("DB_PASSWORD", "StrongPass123"),
    "database": os.getenv("DB_NAME", "license_system"),
}

# Function để lấy kết nối database
def get_db_connection():
    try:
        print(f"[MySQL] Đang kết nối với database... Config: {db_config}")
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print(f"[MySQL] Kết nối thành công với database {db_config['database']}")
            return connection
        else:
            print(f"[MySQL] Không thể kết nối với database mặc dù không có lỗi")
            raise HTTPException(status_code=500, detail="Không thể kết nối với database")
    except Error as e:
        print(f"[MySQL Error] Lỗi kết nối MySQL: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi kết nối MySQL: {e}")

# Hàm thực thi truy vấn và chuyển đổi kết quả sang dict
def execute_query(sql, params=None, fetch=True, many=False):
    try:
        print(f"[SQL Query] Thực thi: {sql}")
        if params:
            print(f"[SQL Params] {params}")
            
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute(sql, params)
        result = None
        
        # Các truy vấn thay đổi dữ liệu (INSERT, UPDATE, DELETE)
        if not fetch:
            connection.commit()
            affected_rows = cursor.rowcount
            print(f"[SQL Result] Số dòng ảnh hưởng: {affected_rows}")
            result = {"affected_rows": affected_rows}
        # Các truy vấn lấy dữ liệu (SELECT)
        else:
            if many:
                result = cursor.fetchall()
                print(f"[SQL Result] Lấy nhiều dòng: {len(result)} kết quả")
            else:
                # Đối với truy vấn có thể trả về nhiều dòng nhưng chỉ muốn lấy một dòng
                # Ta vẫn phải đọc hết tất cả các dòng để tránh lỗi "Unread result found"
                one_result = cursor.fetchone()
                # Đọc hết các dòng còn lại (nếu có) để tránh lỗi
                remaining = cursor.fetchall()
                if remaining:
                    print(f"[SQL Warning] Còn {len(remaining)} dòng kết quả chưa đọc, đã đọc hết để tránh lỗi")
                result = one_result
                print(f"[SQL Result] Lấy một dòng: {result}")
            
        cursor.close()
        connection.close()
        return result
    except (Exception, Error) as e:
        print(f"[SQL Error] Lỗi thực thi truy vấn: {e}")
        raise Exception(f"Lỗi thực thi truy vấn: {e}")

# Model cho tất cả các thao tác
class QueryRequest(BaseModel):
    sql: str
    params: Optional[List[Any]] = None

# Model cho User
class UserCreate(BaseModel):
    username: str
    password_hash: str
    role: Optional[str] = "staff"

# Model cho Device Check
class DeviceCheck(BaseModel):
    mac: str
    hostname: str

# Model cho Device
class DeviceCreate(BaseModel):
    mac: str
    hostname: str
    key_code: str
    added_by: Optional[int] = 1
    expires_at: Optional[str] = None

# Model cho Log
class LogCreate(BaseModel):
    mac: str
    hostname: str
    action: str
    performed_by: Optional[int] = 1

# Model cho Device Activate
class DeviceActivate(BaseModel):
    active: bool = True
    
# Model cho Device Update
class DeviceUpdate(BaseModel):
    active: Optional[int] = None
    activated_at: Optional[str] = None
    expires_at: Optional[str] = None

# Model cho Device Activate With Key
class DeviceActivateWithKey(BaseModel):
    mac: str
    hostname: str
    key_code: str
    
# Model cho Log
class LogCreate(BaseModel):
    mac: str
    hostname: str
    action: str
    performed_by: Optional[int] = 1

# Permission constants - phải đồng bộ với thư viện auth.ts
class Permissions:
    VIEW_DASHBOARD = 'view_dashboard'      # Xem bảng điều khiển cơ bản
    VIEW_KEYS = 'view_keys'               # Xem thông tin key
    MANAGE_KEYS = 'manage_keys'           # Quản lý key (tạo, xóa)
    VIEW_DEVICES = 'view_devices'         # Xem thiết bị
    MANAGE_DEVICES = 'manage_devices'     # Quản lý thiết bị (reset)
    VIEW_LOGS = 'view_logs'               # Xem nhật ký
    MANAGE_LOGS = 'manage_logs'           # Quản lý nhật ký (xóa)
    MANAGE_USERS = 'manage_users'         # Quản lý người dùng
    GRANT_PERMISSIONS = 'grant_permissions' # Cấp quyền cho người dùng khác

# Models
class PermissionRequest(BaseModel):
    user_id: int
    permission: str

class PermissionCheck(BaseModel):
    user_id: int
    permission: str

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Key Management Colony API Server", "status": "running"}

# Test insert thử nghiệm
@app.get("/test-insert")  # Thay đổi path thành /test-insert thay vì /api/test-insert
async def test_insert():
    try:
        return {
            "success": True,
            "message": "Endpoint test-insert hoạt động"
        }
    except Exception as e:
        print(f"[TEST INSERT ERROR] {str(e)}")
        return {"success": False, "message": f"Lỗi: {str(e)}"}

# Test insert MySQL
@app.get("/api/test-insert-mysql")
async def test_insert_mysql():
    try:
        # 1. Kết nối trực tiếp MySQL
        connection = mysql.connector.connect(**db_config)
        if not connection.is_connected():
            return {"success": False, "message": "Không thể kết nối MySQL"}
        
        cursor = connection.cursor()
        
        # 2. Thử INSERT
        test_username = f"test_user_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        test_password = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # 'password' đã hash
        
        print(f"Thử chèn người dùng mới: {test_username}")
        
        # 3. Thực hiện truy vấn INSERT
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (%s, %s, %s, NOW())",
            [test_username, test_password, "user"]
        )
        
        # 4. Commit thay đổi
        connection.commit()
        last_id = cursor.lastrowid
        
        cursor.close()
        connection.close()
        
        return {
            "success": True, 
            "message": "Test INSERT thành công", 
            "username": test_username,
            "id": last_id
        }
    except Exception as e:
        print(f"[TEST INSERT ERROR] {str(e)}")
        return {"success": False, "message": f"Lỗi: {str(e)}"}

# Test kết nối
@app.get("/api/test-connection")
async def test_connection():
    try:
        connection = get_db_connection()
        connection.close()
        return {"success": True, "message": "Database connection successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generic query endpoint
@app.post("/api/query")
async def execute_generic_query(request: QueryRequest):
    # Security check - Prevent certain dangerous operations
    sql_lower = request.sql.lower()
    if "drop table" in sql_lower or "truncate table" in sql_lower:
        raise HTTPException(
            status_code=403, 
            detail="Operation not allowed"
        )
    
    try:
        # Determine if we need to fetch results
        is_select = sql_lower.startswith("select")
        result = execute_query(request.sql, request.params, fetch=is_select, many=is_select)
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}"
        )

# ==== DEVICES ENDPOINTS ====

# Check device activation status
@app.post("/api/devices/check")
async def check_device_status(device: DeviceCheck):
    try:
        print(f"[API] Kiểm tra thiết bị: MAC={device.mac}, Hostname={device.hostname}")
        # Kiểm tra thiết bị có tồn tại trong database không
        existing_device = execute_query(
            "SELECT id, mac, hostname, key_code, active FROM devices WHERE mac = %s AND hostname = %s",
            [device.mac, device.hostname],
            fetch=True,
            many=False
        )
        
        if existing_device:
            return {
                "status": "success",
                "active": bool(existing_device['active']),
                "message": "Device found",
                "device_id": existing_device['id'],
                "key_code": existing_device['key_code'] if existing_device['key_code'] else None
            }
        else:
            # Tự động tạo thiết bị mới khi chưa tồn tại
            print(f"[API] Thiết bị chưa tồn tại, thêm mới: MAC={device.mac}, Hostname={device.hostname}")
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Chưa tạo key, để admin tạo sau
            new_device = execute_query(
                "INSERT INTO devices (mac, hostname, active, created_at) VALUES (%s, %s, %s, %s)",
                [device.mac, device.hostname, 0, now],
                fetch=False
            )
            
            device_id = new_device["last_insert_id"]
            
            return {
                "status": "success",
                "active": False,
                "message": "New device registered",
                "device_id": device_id,
                "key_code": None
            }
    except Exception as e:
        error_msg = f"Error checking device: {str(e)}"
        print(f"[API Error] {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

# Get all devices
@app.get("/api/devices")
async def get_all_devices():
    try:
        devices = execute_query("SELECT * FROM devices ORDER BY id DESC", fetch=True, many=True)
        return {"success": True, "data": devices}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching devices: {str(e)}"
        )

# Get device by ID
@app.get("/api/devices/{device_id}")
async def get_device(device_id: int):
    try:
        device = execute_query("SELECT * FROM devices WHERE id = %s", [device_id], fetch=True, many=False)
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return {"success": True, "data": device}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching device: {str(e)}"
        )

# Helper để chuyển đổi định dạng ISO date thành MySQL datetime
def convert_iso_to_mysql_date(iso_date):
    if not iso_date:
        return None
    try:
        # Xử lý định dạng ISO với timezone (Z)
        if 'T' in iso_date and ('Z' in iso_date or '+' in iso_date or '-' in iso_date):
            # Trích xuất phần ngày tháng năm
            date_part = iso_date.split('T')[0]
            # Nếu cần phần giờ, có thể bổ sung thêm
            return date_part
        return iso_date
    except Exception as e:
        print(f"[Date Conversion Error] {e}")
        return None

# Update device - set expiration and activation
@app.put("/api/devices/{device_id}/update")
async def update_device(device_id: int, update: DeviceUpdate):
    try:
        print(f"[API] Nhận yêu cầu cập nhật thiết bị ID={device_id}: {update.dict()}")
        # Update device with new status
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare update fields
        update_params = []
        update_values = []
        
        if update.active is not None:
            update_params.append("active = %s")
            update_values.append(update.active)
        
        if update.activated_at is not None:
            # Chuyển đổi định dạng ngày
            mysql_date = convert_iso_to_mysql_date(update.activated_at)
            print(f"[API] Chuyển đổi activated_at từ {update.activated_at} thành {mysql_date}")
            update_params.append("activated_at = %s")
            update_values.append(mysql_date)
        elif update.active == 1:  # If activating but no date provided, use current time
            update_params.append("activated_at = %s")
            update_values.append(now)
        
        if update.expires_at is not None:
            # Chuyển đổi định dạng ngày hết hạn
            mysql_expires = convert_iso_to_mysql_date(update.expires_at)
            print(f"[API] Chuyển đổi expires_at từ {update.expires_at} thành {mysql_expires}")
            update_params.append("expires_at = %s")
            update_values.append(mysql_expires)
        
        if not update_params:
            raise HTTPException(status_code=400, detail="No update fields provided")
        
        # Build update query
        update_sql = f"UPDATE devices SET {', '.join(update_params)} WHERE id = %s"
        update_values.append(device_id)
        
        result = execute_query(
            update_sql,
            update_values,
            fetch=False
        )
        
        if result["affected_rows"] == 0:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return {
            "success": True,
            "message": "Device updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating device: {str(e)}"
        )

# Generate key for device
@app.post("/api/devices/{device_id}/generate-key")
async def generate_key_for_device(device_id: int, user_id: int = Query(..., description="User ID performing the action")):
    try:
        print(f"[API] Tạo key cho thiết bị ID={device_id} bởi người dùng ID={user_id}")
        
        # Kiểm tra quyền người dùng
        users = execute_query(
            "SELECT id, role FROM users WHERE id = %s",
            [user_id]
        )
        
        if not users:
            raise HTTPException(status_code=403, detail="Người dùng không tồn tại")
            
        user = users[0]
        
        # Nếu không phải admin, kiểm tra quyền
        if user["role"] != "admin":
            permissions = execute_query(
                "SELECT id FROM user_permissions WHERE user_id = %s AND permission = %s",
                [user_id, Permissions.MANAGE_KEYS]
            )
            
            if not permissions:
                raise HTTPException(
                    status_code=403, 
                    detail="Bạn không có quyền tạo key cho thiết bị. Chỉ người có quyền 'Quản lý key' mới có thể thực hiện thao tác này."
                )
        
        # Kiểm tra thiết bị tồn tại
        device = execute_query(
            "SELECT * FROM devices WHERE id = %s",
            [device_id]
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Sinh key ngẫu nhiên
        key = generate_random_key()
        current_time = datetime.datetime.now()
        expires_at = current_time + datetime.timedelta(days=365)  # Hết hạn sau 1 năm
        
        # Cập nhật key cho thiết bị
        result = execute_query(
            "UPDATE devices SET key_code = %s, expires_at = %s WHERE id = %s",
            [key, expires_at.strftime("%Y-%m-%d %H:%M:%S"), device_id],
            fetch=False
        )
        
        # Thêm log
        try:
            execute_query(
                "INSERT INTO logs (mac, hostname, action, performed_by, timestamp) VALUES (%s, %s, %s, %s, NOW())",
                [device[0]['mac'], device[0]['hostname'], "generate_key", user_id],
                fetch=False
            )
        except Exception as log_error:
            print(f"[API Warning] Lỗi ghi log: {str(log_error)}")
        
        return {
            "success": True,
            "message": "Key generated successfully",
            "key": key,
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating key: {str(e)}"
        )

# Create new device
@app.post("/api/devices")
async def create_device(device: DeviceCreate):
    try:
        result = execute_query(
            "INSERT INTO devices (mac, hostname, key_code, active, added_by, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
            [device.mac, device.hostname, device.key_code, 0, device.added_by],
            fetch=False
        )
        
        return {
            "success": True,
            "message": "Device created successfully",
            "deviceId": result["last_insert_id"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating device: {str(e)}"
        )

# Delete a device
@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: int):
    try:
        result = execute_query(
            "DELETE FROM devices WHERE id = %s",
            [device_id],
            fetch=False
        )
        
        if result["affected_rows"] == 0:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return {"success": True, "message": "Device deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting device: {str(e)}"
        )

# Activate a device by ID
@app.put("/api/devices/{device_id}/activate")
async def activate_device_by_id(device_id: int, activate: DeviceActivate):
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        result = execute_query(
            "UPDATE devices SET active = %s, activated_at = %s WHERE id = %s",
            [1 if activate.active else 0, now if activate.active else None, device_id],
            fetch=False
        )
        
        if result["affected_rows"] == 0:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return {
            "success": True,
            "message": "Device activated successfully" if activate.active else "Device deactivated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating device activation: {str(e)}"
        )

# Activate a device with key (for client app)
@app.post("/api/devices/activate")
async def activate_device_with_key(device: DeviceActivateWithKey):
    try:
        print(f"[API] Nhận yêu cầu kích hoạt thiết bị: MAC={device.mac}, Hostname={device.hostname}, Key={device.key_code}")
        
        # Kiểm tra xem thiết bị có tồn tại không
        existing_device = execute_query(
            "SELECT id FROM devices WHERE mac = %s AND hostname = %s",
            [device.mac, device.hostname],
            fetch=True, many=False
        )
        
        if not existing_device:
            # Tạo mới thiết bị nếu chưa tồn tại
            print(f"[API] Thiết bị chưa tồn tại, thêm mới: MAC={device.mac}, Hostname={device.hostname}")
            insert_result = execute_query(
                "INSERT INTO devices (mac, hostname, key_code, active, created_at) VALUES (%s, %s, %s, %s, NOW())",
                [device.mac, device.hostname, device.key_code, 0],
                fetch=False
            )
            device_id = insert_result["last_insert_id"]
        else:
            device_id = existing_device["id"]
        
        # Kiểm tra key
        valid_key = execute_query(
            "SELECT id FROM devices WHERE key_code = %s AND active = 0",
            [device.key_code],
            fetch=True, many=False
        )
        
        if not valid_key:
            return {
                "status": "error",
                "message": "Key không hợp lệ hoặc đã được sử dụng"
            }
        
        # Cập nhật trạng thái thiết bị
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        result = execute_query(
            "UPDATE devices SET active = 1, activated_at = %s WHERE id = %s",
            [now, device_id],
            fetch=False
        )
        
        if result["affected_rows"] == 0:
            return {
                "status": "error",
                "message": "Không thể kích hoạt thiết bị"
            }
            
        # Ghi log kích hoạt
        try:
            execute_query(
                "INSERT INTO logs (mac, hostname, action, performed_by, timestamp) VALUES (%s, %s, %s, %s, NOW())",
                [device.mac, device.hostname, "activate", 1],
                fetch=False
            )
        except Exception as log_error:
            print(f"[API Warning] Lỗi ghi log: {str(log_error)}")
        
        return {
            "status": "success",
            "message": "Thiết bị đã được kích hoạt thành công",
            "device_id": device_id,
            "active": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating device activation: {str(e)}"
        )

# Reset device status
@app.post("/api/devices/{device_id}/reset")
async def reset_device(device_id: int, user_id: int = Query(..., description="User ID performing the action")):
    try:
        print(f"[API] Reset thiết bị ID={device_id} bởi người dùng ID={user_id}")
        
        # Kiểm tra quyền người dùng
        users = execute_query(
            "SELECT id, role FROM users WHERE id = %s",
            [user_id]
        )
        
        if not users:
            raise HTTPException(status_code=403, detail="Người dùng không tồn tại")
            
        user = users[0]
        
        # Nếu không phải admin, kiểm tra quyền
        if user["role"] != "admin":
            permissions = execute_query(
                "SELECT id FROM user_permissions WHERE user_id = %s AND permission = %s",
                [user_id, Permissions.MANAGE_DEVICES]
            )
            
            if not permissions:
                raise HTTPException(
                    status_code=403, 
                    detail="Bạn không có quyền reset thiết bị. Chỉ người có quyền 'Quản lý thiết bị' mới có thể thực hiện thao tác này."
                )
        
        # Kiểm tra thiết bị tồn tại
        device = execute_query(
            "SELECT id, mac, hostname FROM devices WHERE id = %s",
            [device_id]
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Cập nhật trạng thái
        result = execute_query(
            "UPDATE devices SET active = 0, activated_at = NULL, key_code = NULL WHERE id = %s",
            [device_id],
            fetch=False
        )
        
        # Thêm log
        try:
            execute_query(
                "INSERT INTO logs (mac, hostname, action, performed_by, timestamp) VALUES (%s, %s, %s, %s, NOW())",
                [device[0]['mac'] if 'mac' in device[0] else 'Unknown', device[0]['hostname'] if 'hostname' in device[0] else 'Unknown', "reset", user_id],
                fetch=False
            )
        except Exception as log_error:
            print(f"[API Warning] Lỗi ghi log: {str(log_error)}")
        
        return {
            "success": True,
            "message": "Device reset successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting device: {str(e)}"
        )

# ==== LOGS ENDPOINTS ====

# Get all logs
@app.get("/api/logs")
async def get_all_logs():
    try:
        logs = execute_query(
            "SELECT * FROM logs ORDER BY timestamp DESC",
            fetch=True,
            many=True
        )
        return {"success": True, "data": logs}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching logs: {str(e)}"
        )

# Create new log
@app.post("/api/logs")
async def create_log(log: LogCreate):
    try:
        result = execute_query(
            "INSERT INTO logs (mac, hostname, action, performed_by, timestamp) VALUES (%s, %s, %s, %s, NOW())",
            [log.mac, log.hostname, log.action, log.performed_by],
            fetch=False
        )
        
        return {
            "success": True,
            "message": "Log created successfully",
            "logId": result["last_insert_id"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating log: {str(e)}"
        )

# Delete a log
@app.delete("/api/logs/{log_id}")
async def delete_log(log_id: int, user_id: int = Query(..., description="User ID performing the action")):
    try:
        # Kiểm tra quyền người dùng
        # Lấy thông tin người dùng
        users = execute_query(
            "SELECT id, role FROM users WHERE id = %s",
            [user_id]
        )
        
        if not users:
            raise HTTPException(status_code=403, detail="Người dùng không tồn tại")
            
        user = users[0]
        
        # Nếu là admin, cho phép thực hiện
        if user["role"] != "admin":
            # Kiểm tra quyền cụ thể
            permissions = execute_query(
                "SELECT id FROM user_permissions WHERE user_id = %s AND permission = %s",
                [user_id, Permissions.MANAGE_LOGS]
            )
            
            if not permissions:
                raise HTTPException(
                    status_code=403, 
                    detail="Bạn không có quyền xóa nhật ký. Chỉ người có quyền 'Quản lý nhật ký' mới có thể thực hiện thao tác này."
                )
        
        # Thực hiện xóa log
        result = execute_query(
            "DELETE FROM logs WHERE id = %s",
            [log_id],
            fetch=False
        )
        
        if result["affected_rows"] == 0:
            raise HTTPException(status_code=404, detail="Log not found")
        
        return {"success": True, "message": "Log deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting log: {str(e)}"
        )

# Delete all logs
@app.delete("/api/logs")
async def delete_all_logs(user_id: int = Query(..., description="User ID performing the action")):
    try:
        # Kiểm tra quyền người dùng
        # Lấy thông tin người dùng
        users = execute_query(
            "SELECT id, role FROM users WHERE id = %s",
            [user_id]
        )
        
        if not users:
            raise HTTPException(status_code=403, detail="Người dùng không tồn tại")
            
        user = users[0]
        
        # Nếu là admin, cho phép thực hiện
        if user["role"] != "admin":
            # Kiểm tra quyền cụ thể
            permissions = execute_query(
                "SELECT id FROM user_permissions WHERE user_id = %s AND permission = %s",
                [user_id, Permissions.MANAGE_LOGS]
            )
            
            if not permissions:
                raise HTTPException(
                    status_code=403, 
                    detail="Bạn không có quyền xóa nhật ký. Chỉ người có quyền 'Quản lý nhật ký' mới có thể thực hiện thao tác này."
                )
        
        # Thực hiện xóa tất cả logs
        result = execute_query("DELETE FROM logs", fetch=False)
        
        return {
            "success": True,
            "message": "All logs deleted successfully",
            "count": result["affected_rows"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting all logs: {str(e)}"
        )

# ==== USERS ENDPOINTS ====

# Get all users
@app.get("/api/users")
async def get_all_users():
    try:
        users = execute_query(
            "SELECT id, username, role, created_at FROM users ORDER BY id",
            fetch=True,
            many=True
        )
        return {"success": True, "data": users}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching users: {str(e)}"
        )

# Create new user
@app.post("/api/users")
async def create_user(user: UserCreate):
    try:
        print(f"[API] Nhận yêu cầu tạo người dùng mới: {user.dict()}")
        
        # Kết nối trực tiếp MySQL để tránh lỗi
        connection = mysql.connector.connect(**db_config)
        if not connection.is_connected():
            raise Exception("Không thể kết nối MySQL")
            
        cursor = connection.cursor(dictionary=True)
        
        # Kiểm tra username đã tồn tại
        print(f"[Direct SQL] Kiểm tra tên đăng nhập {user.username}")
        cursor.execute("SELECT id FROM users WHERE username = %s", [user.username])
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.close()
            connection.close()
            print(f"[API] Tên đăng nhập {user.username} đã tồn tại")
            return {
                "success": False,
                "message": "Tên đăng nhập đã tồn tại"
            }
        
        # Thêm người dùng mới
        print(f"[Direct SQL] Thêm người dùng mới: {user.username}")
        insert_sql = "INSERT INTO users (username, password_hash, role, created_at) VALUES (%s, %s, %s, NOW())"
        cursor.execute(insert_sql, [user.username, user.password_hash, user.role])
        
        # Nếu là staff, gán quyền xem bảng điều khiển mặc định
        if user.role == 'staff':
            try:
                insert_permission_sql = "INSERT INTO user_permissions (user_id, permission, granted_by, granted_at) VALUES (%s, %s, %s, NOW())"
                cursor.execute(insert_permission_sql, [cursor.lastrowid, Permissions.VIEW_DASHBOARD, 1])  # Admin ID 1 as default granter
            except Exception as e:
                print(f"[Warning] Không thể gán quyền mặc định cho người dùng mới: {e}")
        
        # Đảm bảo commit dữ liệu
        print("[Direct SQL] Đang commit thay đổi...")
        connection.commit()
        last_insert_id = cursor.lastrowid
        
        # Kiểm tra xem người dùng đã được thêm chưa
        cursor.execute("SELECT id FROM users WHERE id = %s", [last_insert_id])
        created_user = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if created_user:
            print(f"[API] Tạo người dùng thành công. ID mới: {last_insert_id}")
            return {
                "success": True,
                "message": "User created successfully",
                "userId": last_insert_id
            }
        else:
            print(f"[API Warning] Không tìm thấy người dùng vừa tạo ID: {last_insert_id}")
            return {
                "success": False,
                "message": "User creation might have failed. Please check database."
            }
    except Exception as e:
        error_msg = f"Error creating user: {str(e)}"
        print(f"[API Error] {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

# Delete a user
@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    try:
        # Prevent deletion of admin user (id = 1)
        if user_id == 1:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete primary admin user"
            )
        
        result = execute_query(
            "DELETE FROM users WHERE id = %s",
            [user_id],
            fetch=False
        )
        
        if result["affected_rows"] == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting user: {str(e)}"
        )

# API endpoints for permission management
# =================================================================

# Get user permissions
@app.get("/api/permissions/{user_id}")
async def get_user_permissions(user_id: int):
    try:
        # Lấy thông tin người dùng
        users = execute_query(
            "SELECT id, username, role FROM users WHERE id = %s",
            [user_id],
            fetch=True,
            many=False
        )
        
        if not users:
            return {"success": False, "message": "Người dùng không tồn tại"}
            
        user = users
        
        # Admin luôn có tất cả các quyền
        if user["role"] == "admin":
            all_permissions = [
                Permissions.VIEW_DASHBOARD,
                Permissions.VIEW_KEYS,
                Permissions.MANAGE_KEYS,
                Permissions.VIEW_DEVICES,
                Permissions.MANAGE_DEVICES,
                Permissions.VIEW_LOGS,
                Permissions.MANAGE_LOGS,
                Permissions.MANAGE_USERS,
                Permissions.GRANT_PERMISSIONS
            ]
            return {"success": True, "permissions": all_permissions, "user": user}
            
        # Trường hợp staff, truy vấn trực tiếp tất cả các quyền
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT permission FROM user_permissions WHERE user_id = %s", [user_id])
            user_permissions = cursor.fetchall()
            cursor.close()
            connection.close()
            
            # Chuyển đổi các quyền thành danh sách
            permission_list = [p["permission"] for p in user_permissions] if user_permissions else []
            
            # Đảm bảo luôn có VIEW_DASHBOARD cho staff
            if Permissions.VIEW_DASHBOARD not in permission_list:
                permission_list.append(Permissions.VIEW_DASHBOARD)
            
            print(f"[API] Lấy được {len(permission_list)} quyền cho user_id={user_id}")
            return {"success": True, "permissions": permission_list, "user": user}
            
        except Exception as db_error:
            print(f"[API Database Error] Lỗi khi truy vấn quyền: {db_error}")
            return {"success": False, "message": f"Lỗi khi truy vấn quyền: {str(db_error)}"}
    
    except Exception as e:
        print(f"[API Error] Error getting permissions: {e}")
        return {"success": False, "message": str(e)}

# Check if user has permission
@app.post("/api/permissions/check")
async def check_permission(request: PermissionCheck):
    try:
        # Lấy thông tin người dùng
        users = execute_query(
            "SELECT id, role FROM users WHERE id = %s",
            [request.user_id]
        )
        
        if not users:
            return {"success": False, "message": "Người dùng không tồn tại", "hasPermission": False}
            
        user = users[0]
        
        # Admin luôn có quyền
        if user["role"] == "admin":
            return {"success": True, "hasPermission": True}
            
        # Tất cả mọi người đều có quyền xem dashboard
        if request.permission == Permissions.VIEW_DASHBOARD:
            return {"success": True, "hasPermission": True}
        
        # Kiểm tra quyền cụ thể
        permissions = execute_query(
            "SELECT id FROM user_permissions WHERE user_id = %s AND permission = %s",
            [request.user_id, request.permission]
        )
        
        return {"success": True, "hasPermission": len(permissions) > 0}
    
    except Exception as e:
        print(f"[API Error] Error checking permission: {e}")
        return {"success": False, "message": str(e), "hasPermission": False}

# Grant permission to user
@app.post("/api/permissions/grant")
async def grant_permission(request: PermissionRequest):
    try:
        # Lấy thông tin người dùng được cấp quyền
        users = execute_query(
            "SELECT id FROM users WHERE id = %s",
            [request.user_id]
        )
        
        if not users:
            return {"success": False, "message": "Người dùng không tồn tại"}
        
        # Kiểm tra xem quyền đã tồn tại chưa
        permissions = execute_query(
            "SELECT id FROM user_permissions WHERE user_id = %s AND permission = %s",
            [request.user_id, request.permission]
        )
        
        if permissions:
            return {"success": True, "message": "Quyền đã được cấp trước đó"}
        
        # Thêm quyền mới
        execute_query(
            "INSERT INTO user_permissions (user_id, permission, granted_by, granted_at) VALUES (%s, %s, %s, NOW())",
            [request.user_id, request.permission, 1],  # Admin ID 1 as default granter
            fetch=False
        )
        
        return {"success": True, "message": "Đã cấp quyền thành công"}
    
    except Exception as e:
        print(f"[API Error] Error granting permission: {e}")
        return {"success": False, "message": str(e)}

# Revoke permission
@app.delete("/api/permissions/revoke")
async def revoke_permission(request: PermissionRequest):
    try:
        # Xóa quyền
        execute_query(
            "DELETE FROM user_permissions WHERE user_id = %s AND permission = %s",
            [request.user_id, request.permission],
            fetch=False
        )
        
        return {"success": True, "message": "Đã hủy quyền thành công"}
    
    except Exception as e:
        print(f"[API Error] Error revoking permission: {e}")
        return {"success": False, "message": str(e)}

# Endpoint cập nhật mật khẩu admin
@app.get("/update-admin-password")
async def update_admin_password():
    try:
        # Hash mới cho mật khẩu Quangduy1805@@
        new_hash = '57d5243f8cc6f65efc289152304ce70477110894b24021306f0bf77e019de06f'
        
        # Cập nhật mật khẩu admin trong cơ sở dữ liệu
        result = execute_query(
            "UPDATE users SET password_hash = %s WHERE username = %s",
            [new_hash, 'admin'],
            fetch=False
        )
        
        # Kiểm tra xem cập nhật đã thành công chưa
        users = execute_query(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            ['admin']
        )
        
        return {
            "success": True, 
            "affected_rows": result["affected_rows"],
            "message": "Đã cập nhật mật khẩu admin thành 'Quangduy1805@@'",
            "admin_info": users
        }
    except Exception as e:
        print(f"[API Error] Lỗi cập nhật mật khẩu admin: {e}")
        return {"success": False, "message": f"Lỗi: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    port = int(os.getenv("PORT", 3001))
    
    # Khởi tạo bảng user_permissions nếu chưa tồn tại
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            permission VARCHAR(50) NOT NULL,
            granted_by INT NOT NULL,
            granted_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (granted_by) REFERENCES users(id),
            UNIQUE KEY unique_user_permission (user_id, permission)
        )
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        print("[Server] Bảng user_permissions đã được kiểm tra/tạo")
    except Exception as e:
        print(f"[Server Warning] Không thể khởi tạo bảng permissions: {e}")
    
    # Bind to all network interfaces (0.0.0.0) to allow connections from other devices
    print(f"\n[Server] Starting API server on 0.0.0.0:{port}")
    print(f"[Server] Server URL for client app: http://<your-ip-here>:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

# Khởi động ứng dụng
if __name__ == "__main__":
    import socket
    # Lấy địa chỉ IP của máy tính này trên mạng
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    port = int(os.getenv("PORT", 3001))
    
    # In ra thong tin ket noi de client app biet (khong dau tieng Viet de tranh loi encoding)
    print(f"\n*** SERVER INFO ***")
    print(f"API Server running at: http://{ip_address}:{port}")
    print(f"CLIENT APP need to connect to: http://{ip_address}:{port}/api")
    print(f"*******************\n")
    
    # Lắng nghe từ mọi IP (0.0.0.0) và bật chế độ tự động reload khi có thay đổi
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
