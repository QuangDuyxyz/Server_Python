import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3308)),
    'user': os.getenv('DB_USER', 'KingAutoColony'),
    'password': os.getenv('DB_PASSWORD', 'StrongPass123'),
    'database': os.getenv('DB_NAME', 'license_system')
}

try:
    # Connect to database
    print("Connecting to database...")
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    
    # Create table if not exists
    create_table_query = """
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
    """
    
    print("Creating user_permissions table...")
    cursor.execute(create_table_query)
    connection.commit()
    
    print("Table user_permissions created successfully!")
    
    # Close connection
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"Error: {e}")
