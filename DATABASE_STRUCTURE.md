# Database Structure

This project uses **two separate SQLite database files** for better organization and separation of concerns.

## 1. Authentication Database (`auth.db`)

**Purpose:** Handles user authentication, login, and registration.

**Tables:**
- `portal_users` - Stores user credentials
  - `id` (INTEGER, PRIMARY KEY)
  - `email` (TEXT, UNIQUE, NOT NULL)
  - `password` (TEXT, NOT NULL) - SHA-256 hashed
  - `created_at` (TIMESTAMP)

**Functions:**
- `init_auth_db()` - Initialize authentication database
- `create_user(email, password)` - Create new user
- `check_user_exists(email)` - Check if user exists
- `verify_credentials(email, password)` - Verify login credentials
- `get_user_by_email(email)` - Get user details
- `hash_password(password)` - Hash password using SHA-256

## 2. Equipment Database (`equipment.db`)

**Purpose:** Stores all equipment, maintenance requests, and technician data.

**Tables:**

### `equipment`
- `id` (INTEGER, PRIMARY KEY)
- `name` (TEXT, NOT NULL)
- `health_percentage` (INTEGER, DEFAULT 100)
- `status` (TEXT, DEFAULT 'active')
- `created_at` (TIMESTAMP)

### `maintenance_requests`
- `id` (INTEGER, PRIMARY KEY)
- `subject` (TEXT, NOT NULL)
- `employee` (TEXT, NOT NULL)
- `technician` (TEXT)
- `category` (TEXT, NOT NULL)
- `stage` (TEXT, DEFAULT 'New Request')
- `company` (TEXT, NOT NULL)
- `status` (TEXT, DEFAULT 'Pending')
- `due_date` (DATE)
- `created_at` (TIMESTAMP)

### `technicians`
- `id` (INTEGER, PRIMARY KEY)
- `name` (TEXT, NOT NULL)
- `utilization_percentage` (INTEGER, DEFAULT 0)
- `status` (TEXT, DEFAULT 'active')
- `created_at` (TIMESTAMP)

**Functions:**
- `init_equipment_db()` - Initialize equipment database
- `get_critical_equipment_count()` - Get count of equipment with health < 30%
- `get_technician_utilization()` - Get average technician utilization
- `get_open_requests()` - Get pending and overdue requests
- `get_maintenance_requests()` - Get all maintenance requests

## Initialization

Both databases are initialized automatically when the application starts using:
```python
init_db()  # Initializes both databases
```

Or individually:
```python
init_auth_db()      # Initialize only auth database
init_equipment_db() # Initialize only equipment database
```

## Benefits of Separation

1. **Security:** Authentication data is isolated from business data
2. **Maintenance:** Easier to backup and manage separately
3. **Scalability:** Can migrate or optimize databases independently
4. **Organization:** Clear separation of concerns

