import sqlite3
import hashlib
from datetime import datetime

def init_db():
    """Initialize the database and create tables"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portal_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            health_percentage INTEGER DEFAULT 100,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            employee TEXT NOT NULL,
            technician TEXT,
            category TEXT NOT NULL,
            stage TEXT DEFAULT 'New Request',
            company TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            utilization_percentage INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data if tables are empty
    cursor.execute('SELECT COUNT(*) FROM equipment')
    if cursor.fetchone()[0] == 0:
        sample_equipment = [
            ('Equipment A', 25),
            ('Equipment B', 28),
            ('Equipment C', 20),
            ('Equipment D', 15),
            ('Equipment E', 29),
        ]
        cursor.executemany('INSERT INTO equipment (name, health_percentage) VALUES (?, ?)', sample_equipment)
    
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests')
    if cursor.fetchone()[0] == 0:
        sample_requests = [
            ('Test activity', 'Mitchell Admin', 'Aka Foster', 'computer', 'New Request', 'My company', 'Pending'),
            ('Server Maintenance', 'John Doe', 'Aka Foster', 'server', 'In Progress', 'My company', 'Pending'),
            ('Network Setup', 'Jane Smith', 'Tech Support', 'network', 'New Request', 'My company', 'Pending'),
        ]
        cursor.executemany('''
            INSERT INTO maintenance_requests (subject, employee, technician, category, stage, company, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_requests)
    
    cursor.execute('SELECT COUNT(*) FROM technicians')
    if cursor.fetchone()[0] == 0:
        sample_technicians = [
            ('Aka Foster', 85),
            ('Tech Support', 70),
            ('Maintenance Team', 60),
        ]
        cursor.executemany('INSERT INTO technicians (name, utilization_percentage) VALUES (?, ?)', sample_technicians)
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password):
    """Create a new portal user"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    try:
        hashed_password = hash_password(password)
        cursor.execute('''
            INSERT INTO portal_users (email, password)
            VALUES (?, ?)
        ''', (email, hashed_password))
        conn.commit()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Email already exists"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def check_user_exists(email):
    """Check if user exists in database"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM portal_users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    return user is not None

def verify_credentials(email, password):
    """Verify user credentials"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    hashed_password = hash_password(password)
    cursor.execute('''
        SELECT id, email FROM portal_users 
        WHERE email = ? AND password = ?
    ''', (email, hashed_password))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return True, user
    return False, None

def get_user_by_email(email):
    """Get user by email"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, email, password FROM portal_users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    return user

def get_critical_equipment_count():
    """Get count of equipment with health < 30%"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM equipment WHERE health_percentage < 30')
    count = cursor.fetchone()[0]
    conn.close()
    
    return count

def get_technician_utilization():
    """Get average technician utilization"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT AVG(utilization_percentage) FROM technicians')
    result = cursor.fetchone()[0]
    conn.close()
    
    return int(result) if result else 0

def get_open_requests():
    """Get pending and overdue requests"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = ?', ('Pending',))
    pending = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = ? AND due_date < date("now")', ('Pending',))
    overdue = cursor.fetchone()[0]
    
    conn.close()
    
    return pending, overdue

def get_maintenance_requests():
    """Get all maintenance requests"""
    conn = sqlite3.connect('gearguard.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT subject, employee, technician, category, stage, company
        FROM maintenance_requests
        ORDER BY created_at DESC
    ''')
    requests = cursor.fetchall()
    conn.close()
    
    return requests

