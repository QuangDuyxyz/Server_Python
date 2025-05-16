import mysql.connector
import os
from dotenv import load_dotenv
import datetime

# Load environment variables from .env file
load_dotenv()

# MySQL connection configuration
db_config = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '3308')),
    'user': os.getenv('DB_USER', 'KingAutoColony'),
    'password': os.getenv('DB_PASSWORD', 'StrongPass123'),
    'database': os.getenv('DB_NAME', 'license_system')
}

print("=== CREATING TEST DEVICE ===")

# Get current timestamp
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Test device data
test_key = "TEST-KEY-12345"
test_mac = "e9:51:61:56:cb:d3"  # MAC address from client app log
test_hostname = "DESKTOP-O0SV4J5"  # Hostname from client app log

try:
    print(f"Connecting to MySQL database {db_config['database']}...")
    conn = mysql.connector.connect(**db_config)
    
    if conn.is_connected():
        print("Connection successful!")
        cursor = conn.cursor(dictionary=True)
        
        # Check if device already exists
        print(f"Checking if device {test_mac} already exists...")
        cursor.execute("SELECT id FROM devices WHERE mac = %s AND hostname = %s", 
                      [test_mac, test_hostname])
        existing_device = cursor.fetchone()
        
        if existing_device:
            device_id = existing_device['id']
            print(f"Device already exists with ID: {device_id}")
            
            # Update the device with a new key
            print(f"Updating device with new key: {test_key}")
            cursor.execute(
                "UPDATE devices SET key_code = %s, active = 0, activated_at = NULL WHERE id = %s",
                [test_key, device_id]
            )
        else:
            # Create a new device
            print(f"Creating new device: MAC={test_mac}, Hostname={test_hostname}, Key={test_key}")
            cursor.execute(
                "INSERT INTO devices (mac, hostname, key_code, active, created_at) VALUES (%s, %s, %s, %s, %s)",
                [test_mac, test_hostname, test_key, 0, now]
            )
            device_id = cursor.lastrowid
            print(f"New device created with ID: {device_id}")
        
        # Create another test device with a different key if needed
        alt_key = "DEMO-KEY-67890"
        print(f"Creating additional test device with key: {alt_key}")
        cursor.execute(
            "INSERT INTO devices (mac, hostname, key_code, active, created_at) VALUES (%s, %s, %s, %s, %s)",
            ["00:11:22:33:44:55", "TEST-PC", alt_key, 0, now]
        )
        print(f"Additional test device created with ID: {cursor.lastrowid}")
        
        # Commit changes
        conn.commit()
        print("Changes committed to database")
        
        # Display all devices
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()
        print("\n=== ALL DEVICES ===")
        for device in devices:
            print(f"ID: {device['id']} | MAC: {device['mac']} | Hostname: {device['hostname']} | Key: {device['key_code']} | Active: {device['active']}")
        
except Exception as e:
    print(f"ERROR: {str(e)}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("MySQL connection closed")
