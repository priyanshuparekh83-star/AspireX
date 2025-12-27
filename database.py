import sqlite3
import hashlib
from datetime import datetime

# Database file names
AUTH_DB = 'auth.db'
EQUIPMENT_DB = 'equipment.db'
REQUESTS_DB = 'requests.db'

# ==================== AUTHENTICATION DATABASE FUNCTIONS ====================

def init_auth_db():
    """Initialize the authentication database for login/register"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portal_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Authentication database '{AUTH_DB}' initialized successfully")

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password):
    """Create a new portal user in auth database"""
    conn = sqlite3.connect(AUTH_DB)
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
    """Check if user exists in auth database"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM portal_users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    return user is not None

def verify_credentials(email, password):
    """Verify user credentials from auth database"""
    conn = sqlite3.connect(AUTH_DB)
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
    """Get user by email from auth database"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, email, password FROM portal_users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    return user

# ==================== EQUIPMENT DATABASE FUNCTIONS ====================

def migrate_maintenance_requests_table(cursor):
    """Add missing columns to maintenance_requests table if they don't exist"""
    # Get table info to check existing columns
    cursor.execute("PRAGMA table_info(maintenance_requests)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    # List of columns to add (SQLite ALTER TABLE doesn't support DEFAULT in ADD COLUMN)
    columns_to_add = [
        ('request_type', 'TEXT'),
        ('priority', 'TEXT'),
        ('description', 'TEXT'),
        ('scheduled_date', 'DATE'),
        ('due_date', 'DATE'),
        ('equipment_id', 'INTEGER'),
        ('team', 'TEXT'),
        ('request_date', 'DATE'),
        ('duration', 'TEXT'),
    ]
    
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE maintenance_requests ADD COLUMN {column_name} {column_type}')
                print(f"Added column '{column_name}' to maintenance_requests table")
                # Set default values for existing rows
                if column_name == 'request_type':
                    cursor.execute("UPDATE maintenance_requests SET request_type = 'Corrective (Breakdown)' WHERE request_type IS NULL")
                elif column_name == 'priority':
                    cursor.execute("UPDATE maintenance_requests SET priority = 'Medium' WHERE priority IS NULL")
            except sqlite3.OperationalError as e:
                print(f"Could not add column '{column_name}': {e}")

def migrate_equipment_table(cursor):
    """Add missing columns to equipment table if they don't exist"""
    cursor.execute("PRAGMA table_info(equipment)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    columns_to_add = [
        ('employee', 'TEXT'),
        ('department', 'TEXT'),
        ('serial_number', 'TEXT'),
        ('technician', 'TEXT'),
        ('equipment_category_id', 'INTEGER'),
        ('company', 'TEXT'),
        ('used_by', 'TEXT'),
        ('maintenance_team', 'TEXT'),
        ('assigned_date', 'DATE'),
        ('description', 'TEXT'),
        ('scrap_date', 'DATE'),
        ('used_in_location', 'TEXT'),
        ('work_center_id', 'INTEGER'),
    ]
    
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE equipment ADD COLUMN {column_name} {column_type}')
                print(f"Added column '{column_name}' to equipment table")
            except sqlite3.OperationalError as e:
                print(f"Could not add column '{column_name}': {e}")

def init_equipment_db():
    """Initialize the equipment database"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    # Equipment table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            health_percentage INTEGER DEFAULT 100,
            status TEXT DEFAULT 'active',
            employee TEXT,
            department TEXT,
            serial_number TEXT,
            technician TEXT,
            equipment_category_id INTEGER,
            company TEXT DEFAULT 'My Company (San Francisco)',
            used_by TEXT,
            maintenance_team TEXT,
            assigned_date DATE,
            description TEXT,
            scrap_date DATE,
            used_in_location TEXT,
            work_center_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migrate existing table to add new columns
    migrate_equipment_table(cursor)
    
    # Maintenance requests table - create with basic structure first
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            employee TEXT NOT NULL,
            technician TEXT,
            category TEXT NOT NULL,
            stage TEXT DEFAULT 'New',
            company TEXT NOT NULL,
            status TEXT DEFAULT 'New',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migrate existing table to add new columns
    migrate_maintenance_requests_table(cursor)
    
    # For new installations, ensure all columns exist with proper defaults
    # Check if request_type column exists, if not, the migration above should have added it
    cursor.execute("PRAGMA table_info(maintenance_requests)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # If table was just created, it won't have the new columns, so add them
    if 'request_type' not in columns:
        migrate_maintenance_requests_table(cursor)
    
    # Technicians table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            utilization_percentage INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Maintenance teams table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Team members table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            technician_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES maintenance_teams(id),
            FOREIGN KEY (technician_id) REFERENCES technicians(id)
        )
    ''')
    
    # Profiles table (linked to auth users)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # User roles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Equipment categories table (should be in equipment DB for joins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            responsible TEXT,
            company TEXT DEFAULT 'My Company (San Francisco)',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sample data insertion removed - database will start empty
    # Users can add data through the application interface
    
    conn.commit()
    conn.close()
    print(f"Equipment database '{EQUIPMENT_DB}' initialized successfully")

def get_critical_equipment_count():
    """Get count of equipment with health < 30% from equipment database"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM equipment WHERE health_percentage < 30')
    count = cursor.fetchone()[0]
    conn.close()
    
    return count

def get_technician_utilization():
    """Get average technician utilization from equipment database"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT AVG(utilization_percentage) FROM technicians')
    result = cursor.fetchone()[0]
    conn.close()
    
    return int(result) if result else 0

def get_open_requests():
    """Get pending and overdue requests from equipment database"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = ?', ('Pending',))
    pending = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = ? AND due_date < date("now")', ('Pending',))
    overdue = cursor.fetchone()[0]
    
    conn.close()
    
    return pending, overdue

def get_maintenance_requests(status=None):
    """Get all maintenance requests from equipment database"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    if status:
        cursor.execute('''
            SELECT id, subject, employee, technician, category, stage, company, status, request_type, priority, description, scheduled_date, due_date, team, request_date, duration
            FROM maintenance_requests
            WHERE status = ?
            ORDER BY created_at DESC
        ''', (status,))
    else:
        cursor.execute('''
            SELECT id, subject, employee, technician, category, stage, company, status, request_type, priority, description, scheduled_date, due_date, team, request_date, duration
            FROM maintenance_requests
            ORDER BY created_at DESC
        ''')
    requests = cursor.fetchall()
    conn.close()
    
    return requests

def get_maintenance_requests_simple():
    """Get maintenance requests in simple format for dashboard table"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT subject, employee, technician, category, stage, company
        FROM maintenance_requests
        ORDER BY created_at DESC
        LIMIT 50
    ''')
    requests = cursor.fetchall()
    conn.close()
    
    return requests

def get_all_equipment():
    """Get all equipment with category name"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.id, e.name, e.health_percentage, e.status, e.employee, e.department, 
               e.serial_number, e.technician, e.equipment_category_id, e.company,
               e.used_by, e.maintenance_team, e.assigned_date, e.description,
               e.scrap_date, e.used_in_location, e.work_center_id, e.created_at,
               ec.name as category_name
        FROM equipment e
        LEFT JOIN equipment_categories ec ON e.equipment_category_id = ec.id
        ORDER BY e.name
    ''')
    equipment = cursor.fetchall()
    conn.close()
    
    return equipment

def get_equipment_by_id(equipment_id):
    """Get equipment by ID"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.id, e.name, e.health_percentage, e.status, e.employee, e.department, 
               e.serial_number, e.technician, e.equipment_category_id, e.company,
               e.used_by, e.maintenance_team, e.assigned_date, e.description,
               e.scrap_date, e.used_in_location, e.work_center_id, e.created_at,
               ec.name as category_name
        FROM equipment e
        LEFT JOIN equipment_categories ec ON e.equipment_category_id = ec.id
        WHERE e.id = ?
    ''', (equipment_id,))
    equipment = cursor.fetchone()
    conn.close()
    
    return equipment

def create_equipment(name, employee=None, department=None, serial_number=None, technician=None, 
                     equipment_category_id=None, company=None, used_by=None, maintenance_team=None,
                     assigned_date=None, description=None, scrap_date=None, used_in_location=None,
                     work_center_id=None, health_percentage=100, status='active'):
    """Create new equipment"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO equipment (name, employee, department, serial_number, technician, 
                                 equipment_category_id, company, used_by, maintenance_team,
                                 assigned_date, description, scrap_date, used_in_location,
                                 work_center_id, health_percentage, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, employee, department, serial_number, technician, equipment_category_id,
              company or 'My Company (San Francisco)', used_by, maintenance_team,
              assigned_date, description, scrap_date, used_in_location, work_center_id,
              health_percentage, status))
        conn.commit()
        return True, cursor.lastrowid
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def update_equipment(equipment_id, name, employee=None, department=None, serial_number=None, 
                     technician=None, equipment_category_id=None, company=None, used_by=None,
                     maintenance_team=None, assigned_date=None, description=None, scrap_date=None,
                     used_in_location=None, work_center_id=None, health_percentage=100, status='active'):
    """Update equipment"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE equipment SET name=?, employee=?, department=?, serial_number=?, technician=?,
                               equipment_category_id=?, company=?, used_by=?, maintenance_team=?,
                               assigned_date=?, description=?, scrap_date=?, used_in_location=?,
                               work_center_id=?, health_percentage=?, status=?
            WHERE id=?
        ''', (name, employee, department, serial_number, technician, equipment_category_id,
              company, used_by, maintenance_team, assigned_date, description, scrap_date,
              used_in_location, work_center_id, health_percentage, status, equipment_id))
        conn.commit()
        return True, "Equipment updated successfully"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def delete_equipment(equipment_id):
    """Delete equipment"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM equipment WHERE id=?', (equipment_id,))
        conn.commit()
        return True, "Equipment deleted successfully"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def create_maintenance_request(subject, employee, equipment_id, request_type, priority, description, scheduled_date, due_date, company='My company', team=None, technician=None, category=None, request_date=None, duration=None):
    """Create a new maintenance request"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    try:
        # Get equipment name for category if not provided
        if not category and equipment_id:
            cursor.execute('SELECT name FROM equipment WHERE id = ?', (equipment_id,))
            eq_result = cursor.fetchone()
            if eq_result:
                category = eq_result[0]
        
        # Use current date if request_date not provided
        if not request_date:
            from datetime import datetime
            request_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO maintenance_requests (subject, employee, equipment_id, request_type, priority, description, scheduled_date, due_date, company, status, stage, team, technician, category, request_date, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', 'New', ?, ?, ?, ?, ?)
        ''', (subject, employee, equipment_id, request_type, priority, description, scheduled_date, due_date, company, team, technician, category, request_date, duration))
        conn.commit()
        return True, "Request created successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def update_request_status(request_id, status):
    """Update maintenance request status"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE maintenance_requests 
            SET status = ?, stage = ?
            WHERE id = ?
        ''', (status, status, request_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_dashboard_stats():
    """Get dashboard statistics"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    
    # Total equipment
    cursor.execute('SELECT COUNT(*) FROM equipment')
    total_equipment = cursor.fetchone()[0]
    
    # Open requests
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status IN ("New", "In Progress")')
    open_requests = cursor.fetchone()[0]
    
    # In progress
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = "In Progress"')
    in_progress = cursor.fetchone()[0]
    
    # Completed
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = "Repaired"')
    completed = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_equipment': total_equipment,
        'open_requests': open_requests,
        'in_progress': in_progress,
        'completed': completed
    }

def get_user_signups():
    """Get user signups for chart (last 7 days)"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM portal_users
        WHERE created_at >= date('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date
    ''')
    signups = cursor.fetchall()
    conn.close()
    
    return signups

def get_all_users():
    """Get all users with profile information"""
    conn_auth = sqlite3.connect(AUTH_DB)
    conn_equip = sqlite3.connect(EQUIPMENT_DB)
    
    cursor_auth = conn_auth.cursor()
    cursor_equip = conn_equip.cursor()
    
    cursor_auth.execute('SELECT id, email, created_at FROM portal_users ORDER BY created_at DESC')
    users = cursor_auth.fetchall()
    
    result = []
    for user in users:
        user_id, email, created_at = user
        cursor_equip.execute('SELECT full_name, phone, role FROM profiles WHERE user_id = ?', (user_id,))
        profile = cursor_equip.fetchone()
        
        result.append({
            'id': user_id,
            'email': email,
            'full_name': profile[0] if profile else None,
            'phone': profile[1] if profile else None,
            'role': profile[2] if profile else 'user',
            'created_at': created_at
        })
    
    conn_auth.close()
    conn_equip.close()
    
    return result

# ==================== REQUESTS DATABASE FUNCTIONS ====================

def init_requests_db():
    """Initialize the requests database for storing maintenance requests"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    # Maintenance requests table with all columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            employee TEXT NOT NULL,
            technician TEXT,
            category TEXT,
            stage TEXT DEFAULT 'New',
            company TEXT NOT NULL DEFAULT 'My company',
            status TEXT DEFAULT 'New',
            request_type TEXT,
            priority TEXT DEFAULT 'Medium',
            description TEXT,
            scheduled_date DATE,
            due_date DATE,
            equipment_id INTEGER,
            work_center_id INTEGER,
            maintenance_for TEXT DEFAULT 'Equipment',
            notes TEXT,
            instructions TEXT,
            team TEXT,
            request_date DATE DEFAULT CURRENT_DATE,
            duration TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migrate existing table to add new columns
    cursor.execute("PRAGMA table_info(maintenance_requests)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    columns_to_add = [
        ('work_center_id', 'INTEGER'),
        ('maintenance_for', 'TEXT DEFAULT "Equipment"'),
        ('notes', 'TEXT'),
        ('instructions', 'TEXT')
    ]
    
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE maintenance_requests ADD COLUMN {column_name} {column_type}')
                print(f"Added column '{column_name}' to maintenance_requests table")
            except sqlite3.OperationalError as e:
                print(f"Could not add column '{column_name}': {e}")
    
    # Worksheet comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worksheet_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            user TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES maintenance_requests(id)
        )
    ''')
    
    # Work centers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            tag TEXT,
            alternative_workcenters TEXT,
            cost_per_hour REAL DEFAULT 0.0,
            capacity_time_efficiency REAL DEFAULT 100.0,
            oee_target REAL DEFAULT 0.0,
            company TEXT DEFAULT 'My company',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Equipment categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            responsible TEXT,
            company TEXT DEFAULT 'My company',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Requests database '{REQUESTS_DB}' initialized successfully")

def create_maintenance_request_new(subject, employee, equipment_id=None, request_type='Corrective', priority='Medium', description=None, scheduled_date=None, due_date=None, company='My company', team=None, technician=None, category=None, request_date=None, duration=None, work_center_id=None, maintenance_for='Equipment', notes=None, instructions=None):
    """Create a new maintenance request in the requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    try:
        # Get equipment name for category if not provided
        if not category and equipment_id:
            conn_equip = sqlite3.connect(EQUIPMENT_DB)
            cursor_equip = conn_equip.cursor()
            cursor_equip.execute('SELECT name FROM equipment WHERE id = ?', (equipment_id,))
            eq_result = cursor_equip.fetchone()
            if eq_result:
                category = eq_result[0]
            conn_equip.close()
        
        # Use current date if request_date not provided
        if not request_date:
            request_date = datetime.now().strftime('%Y-%m-%d')
        
        # Convert equipment_id and work_center_id to integers or None
        equipment_id_int = int(equipment_id) if equipment_id and str(equipment_id).strip() else None
        work_center_id_int = int(work_center_id) if work_center_id and str(work_center_id).strip() else None
        
        cursor.execute('''
            INSERT INTO maintenance_requests (subject, employee, equipment_id, work_center_id, maintenance_for, request_type, priority, description, scheduled_date, due_date, company, status, stage, team, technician, category, request_date, duration, notes, instructions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', 'New', ?, ?, ?, ?, ?, ?, ?)
        ''', (subject, employee, equipment_id_int, work_center_id_int, maintenance_for, request_type, priority, description, scheduled_date, due_date, company, team, technician, category, request_date, duration, notes, instructions))
        conn.commit()
        return True, "Request created successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def get_maintenance_requests_new(status=None):
    """Get maintenance requests from the requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    if status:
        cursor.execute('''
            SELECT * FROM maintenance_requests
            WHERE status = ?
            ORDER BY created_at DESC
        ''', (status,))
    else:
        cursor.execute('''
            SELECT * FROM maintenance_requests
            ORDER BY created_at DESC
        ''')
    
    requests = cursor.fetchall()
    conn.close()
    
    # Get equipment names from equipment database and append to results
    if requests:
        conn_equip = sqlite3.connect(EQUIPMENT_DB)
        cursor_equip = conn_equip.cursor()
        result = []
        for req in requests:
            req_list = list(req)
            # equipment_id is at index 13 (0-indexed)
            if len(req_list) > 13 and req_list[13]:
                cursor_equip.execute('SELECT name FROM equipment WHERE id = ?', (req_list[13],))
                eq_result = cursor_equip.fetchone()
                equipment_name = eq_result[0] if eq_result else None
            else:
                equipment_name = None
            # Append equipment_name to the tuple
            req_list.append(equipment_name)
            result.append(tuple(req_list))
        conn_equip.close()
        return result
    
    return requests

def get_maintenance_requests_simple_new():
    """Get all maintenance requests in simple format from requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM maintenance_requests
        ORDER BY created_at DESC
        LIMIT 50
    ''')
    requests = cursor.fetchall()
    conn.close()
    
    # Get equipment names from equipment database and append to results
    if requests:
        conn_equip = sqlite3.connect(EQUIPMENT_DB)
        cursor_equip = conn_equip.cursor()
        result = []
        for req in requests:
            req_list = list(req)
            # equipment_id is at index 13 (0-indexed)
            if len(req_list) > 13 and req_list[13]:
                cursor_equip.execute('SELECT name FROM equipment WHERE id = ?', (req_list[13],))
                eq_result = cursor_equip.fetchone()
                equipment_name = eq_result[0] if eq_result else None
            else:
                equipment_name = None
            # Append equipment_name to the tuple
            req_list.append(equipment_name)
            result.append(tuple(req_list))
        conn_equip.close()
        return result
    
    return requests

def update_request_status_new(request_id, status):
    """Update maintenance request status in requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE maintenance_requests 
            SET status = ?, stage = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, status, request_id))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def get_dashboard_stats_new():
    """Get dashboard statistics from requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    # Open requests
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status IN ("New", "In Progress")')
    open_requests = cursor.fetchone()[0]
    
    # In progress
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = "In Progress"')
    in_progress = cursor.fetchone()[0]
    
    # Completed
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests WHERE status = "Repaired"')
    completed = cursor.fetchone()[0]
    
    # Total requests
    cursor.execute('SELECT COUNT(*) FROM maintenance_requests')
    total_requests = cursor.fetchone()[0]
    
    # Overdue requests (due_date in past and status not completed)
    cursor.execute('''
        SELECT COUNT(*) FROM maintenance_requests 
        WHERE due_date IS NOT NULL 
        AND due_date < date('now') 
        AND status NOT IN ('Repaired', 'Scrap')
    ''')
    overdue = cursor.fetchone()[0]
    
    conn.close()
    
    # Get equipment stats from equipment database
    conn_equip = sqlite3.connect(EQUIPMENT_DB)
    cursor_equip = conn_equip.cursor()
    cursor_equip.execute('SELECT COUNT(*) FROM equipment')
    total_equipment = cursor_equip.fetchone()[0]
    conn_equip.close()
    
    return {
        'total_equipment': total_equipment,
        'open_requests': open_requests,
        'in_progress': in_progress,
        'completed': completed,
        'total_requests': total_requests,
        'overdue': overdue
    }

def get_maintenance_request_by_id(request_id):
    """Get a single maintenance request by ID from requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM maintenance_requests WHERE id = ?', (request_id,))
    request = cursor.fetchone()
    conn.close()
    
    if request:
        # Get equipment name if equipment_id exists
        req_list = list(request)
        equipment_name = None
        
        if len(req_list) > 13 and req_list[13]:  # equipment_id at index 13
            try:
                conn_equip = sqlite3.connect(EQUIPMENT_DB)
                cursor_equip = conn_equip.cursor()
                cursor_equip.execute('SELECT name FROM equipment WHERE id = ?', (req_list[13],))
                eq_result = cursor_equip.fetchone()
                equipment_name = eq_result[0] if eq_result else None
                conn_equip.close()
            except Exception as e:
                print(f"Error fetching equipment name: {e}")
                equipment_name = None
        
        # Always append equipment_name (even if None) for consistent tuple structure
        req_list.append(equipment_name)
        return tuple(req_list)
    
    return request

def update_maintenance_request(request_id, subject=None, employee=None, equipment_id=None, request_type=None, priority=None, description=None, scheduled_date=None, due_date=None, company=None, team=None, technician=None, category=None, request_date=None, duration=None, status=None):
    """Update a maintenance request in the requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    try:
        # Build update query dynamically based on provided fields
        updates = []
        values = []
        
        if subject is not None:
            updates.append('subject = ?')
            values.append(subject)
        if employee is not None:
            updates.append('employee = ?')
            values.append(employee)
        if equipment_id is not None:
            updates.append('equipment_id = ?')
            values.append(equipment_id)
        if request_type is not None:
            updates.append('request_type = ?')
            values.append(request_type)
        if priority is not None:
            updates.append('priority = ?')
            values.append(priority)
        if description is not None:
            updates.append('description = ?')
            values.append(description)
        if scheduled_date is not None:
            updates.append('scheduled_date = ?')
            values.append(scheduled_date)
        if due_date is not None:
            updates.append('due_date = ?')
            values.append(due_date)
        if company is not None:
            updates.append('company = ?')
            values.append(company)
        if team is not None:
            updates.append('team = ?')
            values.append(team)
        if technician is not None:
            updates.append('technician = ?')
            values.append(technician)
        if category is not None:
            updates.append('category = ?')
            values.append(category)
        if request_date is not None:
            updates.append('request_date = ?')
            values.append(request_date)
        if duration is not None:
            updates.append('duration = ?')
            values.append(duration)
        if status is not None:
            updates.append('status = ?')
            updates.append('stage = ?')
            values.append(status)
            values.append(status)
        
        if not updates:
            return False, "No fields to update"
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        values.append(request_id)
        
        query = f'UPDATE maintenance_requests SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, values)
        conn.commit()
        return True, "Request updated successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def delete_maintenance_request(request_id):
    """Delete a maintenance request from the requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    try:
        # Delete comments first (foreign key constraint)
        cursor.execute('DELETE FROM worksheet_comments WHERE request_id = ?', (request_id,))
        cursor.execute('DELETE FROM maintenance_requests WHERE id = ?', (request_id,))
        conn.commit()
        return True, "Request deleted successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def get_worksheet_comments(request_id):
    """Get all worksheet comments for a maintenance request"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, request_id, user, comment, created_at
        FROM worksheet_comments
        WHERE request_id = ?
        ORDER BY created_at DESC
    ''', (request_id,))
    
    comments = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for comment in comments:
        result.append({
            'id': comment[0],
            'request_id': comment[1],
            'user': comment[2],
            'comment': comment[3],
            'created_at': comment[4]
        })
    
    return result

def add_worksheet_comment(request_id, user, comment):
    """Add a worksheet comment to a maintenance request"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO worksheet_comments (request_id, user, comment)
            VALUES (?, ?, ?)
        ''', (request_id, user, comment))
        conn.commit()
        return True, "Comment added successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def get_overdue_requests_new():
    """Get count of overdue requests from requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    
    # Overdue requests are those with status 'New' or 'In Progress' and due_date in the past
    cursor.execute('''
        SELECT COUNT(*) FROM maintenance_requests 
        WHERE status IN ("New", "In Progress", "Blocked", "Ready for next stage") 
        AND due_date IS NOT NULL AND due_date < CURRENT_DATE
    ''')
    overdue_count = cursor.fetchone()[0]
    conn.close()
    return overdue_count

# ==================== WORK CENTERS DATABASE FUNCTIONS ====================

def get_all_work_centers():
    """Get all work centers from requests database"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM work_centers ORDER BY name ASC')
    work_centers = cursor.fetchall()
    conn.close()
    return work_centers

def create_work_center(name, code=None, tag=None, alternative_workcenters=None, cost_per_hour=0.0, capacity_time_efficiency=100.0, oee_target=0.0, company='My company'):
    """Create a new work center"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO work_centers (name, code, tag, alternative_workcenters, cost_per_hour, capacity_time_efficiency, oee_target, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, code, tag, alternative_workcenters, cost_per_hour, capacity_time_efficiency, oee_target, company))
        conn.commit()
        return True, "Work center created successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def get_work_center_by_id(work_center_id):
    """Get a work center by ID"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM work_centers WHERE id = ?', (work_center_id,))
    work_center = cursor.fetchone()
    conn.close()
    return work_center

def update_work_center(work_center_id, name=None, code=None, tag=None, alternative_workcenters=None, cost_per_hour=None, capacity_time_efficiency=None, oee_target=None, company=None):
    """Update a work center"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    try:
        updates = []
        values = []
        
        if name is not None:
            updates.append('name = ?')
            values.append(name)
        if code is not None:
            updates.append('code = ?')
            values.append(code)
        if tag is not None:
            updates.append('tag = ?')
            values.append(tag)
        if alternative_workcenters is not None:
            updates.append('alternative_workcenters = ?')
            values.append(alternative_workcenters)
        if cost_per_hour is not None:
            updates.append('cost_per_hour = ?')
            values.append(cost_per_hour)
        if capacity_time_efficiency is not None:
            updates.append('capacity_time_efficiency = ?')
            values.append(capacity_time_efficiency)
        if oee_target is not None:
            updates.append('oee_target = ?')
            values.append(oee_target)
        if company is not None:
            updates.append('company = ?')
            values.append(company)
        
        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            values.append(work_center_id)
            cursor.execute(f'UPDATE work_centers SET {", ".join(updates)} WHERE id = ?', values)
            conn.commit()
            return True, "Work center updated successfully"
        return False, "No fields to update"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def delete_work_center(work_center_id):
    """Delete a work center"""
    conn = sqlite3.connect(REQUESTS_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM work_centers WHERE id = ?', (work_center_id,))
        conn.commit()
        return True, "Work center deleted successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

# ==================== EQUIPMENT CATEGORIES DATABASE FUNCTIONS ====================

def get_all_equipment_categories():
    """Get all equipment categories from equipment database"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment_categories ORDER BY name ASC')
    categories = cursor.fetchall()
    conn.close()
    return categories

def create_equipment_category(name, responsible=None, company='My Company (San Francisco)'):
    """Create a new equipment category"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO equipment_categories (name, responsible, company)
            VALUES (?, ?, ?)
        ''', (name, responsible, company))
        conn.commit()
        return True, "Equipment category created successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def get_equipment_category_by_id(category_id):
    """Get an equipment category by ID"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment_categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    conn.close()
    return category

def update_equipment_category(category_id, name=None, responsible=None, company=None):
    """Update an equipment category"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    try:
        updates = []
        values = []
        
        if name is not None:
            updates.append('name = ?')
            values.append(name)
        if responsible is not None:
            updates.append('responsible = ?')
            values.append(responsible)
        if company is not None:
            updates.append('company = ?')
            values.append(company)
        
        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            values.append(category_id)
            cursor.execute(f'UPDATE equipment_categories SET {", ".join(updates)} WHERE id = ?', values)
            conn.commit()
            return True, "Equipment category updated successfully"
        return False, "No fields to update"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def delete_equipment_category(category_id):
    """Delete an equipment category"""
    conn = sqlite3.connect(EQUIPMENT_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM equipment_categories WHERE id = ?', (category_id,))
        conn.commit()
        return True, "Equipment category deleted successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

# ==================== COMBINED INITIALIZATION ====================

def init_db():
    """Initialize all databases"""
    init_auth_db()
    init_equipment_db()
    init_requests_db()
    print("All databases initialized successfully!")
