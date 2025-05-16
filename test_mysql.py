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

print("=== MYSQL CONNECTION TEST ===")
print(f"Connection info: {db_config}")

# Try to connect
try:
    print("\n1. Connecting to MySQL...")
    conn = mysql.connector.connect(**db_config)
    
    if conn.is_connected():
        print("[SUCCESS] Connection successful!")
        db_info = conn.get_server_info()
        print(f"   Server version: {db_info}")
        
        cursor = conn.cursor()
        
        # Check if users table exists
        print("\n2. Checking users table...")
        cursor.execute("SHOW TABLES LIKE 'users'")
        tables = cursor.fetchall()
        
        if len(tables) > 0:
            print("[SUCCESS] Users table exists!")
            
            # View users table structure
            cursor.execute("DESCRIBE users")
            columns = cursor.fetchall()
            print("\n3. Users table structure:")
            for column in columns:
                print(f"   {column[0]} - {column[1]}")
            
            # View data counts
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            print(f"\n4. Total users: {count}")
            
            # Add test user
            try:
                print("\n5. Trying to create test user...")
                test_username = f"test_user_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                test_password = "test_hash_123456"
                
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, created_at) VALUES (%s, %s, %s, NOW())",
                    [test_username, test_password, "user"]
                )
                
                # Check autocommit status
                print(f"   Autocommit status: {conn.autocommit}")
                
                # Manual commit
                print("   Committing...")
                conn.commit()
                
                last_id = cursor.lastrowid
                print(f"[SUCCESS] User added successfully! ID: {last_id}")
                
                # Verify the new user
                cursor.execute(f"SELECT * FROM users WHERE id = {last_id}")
                new_user = cursor.fetchone()
                if new_user:
                    print(f"[SUCCESS] Confirmed new user: ID={last_id}, Username={test_username}")
                else:
                    print("[WARNING] Could not find the newly added user!")
                
            except Exception as e:
                print(f"[ERROR] Error adding user: {str(e)}")
        else:
            print("[WARNING] Users table does not exist!")
            
            # Create users table
            print("\n3. Creating users table...")
            cursor.execute("""
                CREATE TABLE users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    created_at DATETIME NOT NULL
                )
            """)
            print("[SUCCESS] Users table created!")
    
        cursor.close()        
    else:
        print("[WARNING] Could not connect!")
    
    conn.close()
    print("\nConnection closed.")
    
except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    
    # Display more information for connection errors
    if "Can't connect to MySQL server" in str(e):
        print("\nTroubleshooting tips:")
        print("1. Make sure MySQL is running")
        print("2. Check connection info in .env file")
        print("3. Verify port (3308) is correct")
        print("4. Check username/password")
    elif "Access denied" in str(e):
        print("\nAuthentication error! Check:")
        print("1. Username and password in .env file")
        print(f"2. Permissions for user '{db_config['user']}' on database '{db_config['database']}'")
    elif "Unknown database" in str(e):
        print(f"\nDatabase '{db_config['database']}' doesn't exist! Create it first:")
        print(f"CREATE DATABASE {db_config['database']};")
