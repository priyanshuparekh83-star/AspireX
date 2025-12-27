from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
from database import (
    init_db, create_user, check_user_exists, verify_credentials, get_user_by_email,
    get_critical_equipment_count, get_technician_utilization, get_open_requests, get_maintenance_requests
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production

# Initialize database on startup
init_db()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            return render_template('login.html', error='Please fill in all fields')
        
        # Check if user exists
        if not check_user_exists(email):
            return render_template('login.html', error='Account not exist')
        
        # Verify credentials
        is_valid, user = verify_credentials(email, password)
        
        if is_valid:
            session['user_id'] = user[0]
            session['email'] = user[1]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid Password')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not email or not password or not confirm_password:
            return render_template('signup.html', error='Please fill in all fields')
        
        # Check if email already exists
        if check_user_exists(email):
            return render_template('signup.html', error='Email already exists. Please use a different email.')
        
        # Validate password requirements
        password_errors = validate_password(password)
        if password_errors:
            return render_template('signup.html', error=password_errors)
        
        # Check if passwords match
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        # Create user
        success, message = create_user(email, password)
        
        if success:
            return render_template('signup.html', success='Account created successfully! You can now sign in.')
        else:
            return render_template('signup.html', error=message)
    
    return render_template('signup.html')

@app.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            return render_template('forget_password.html', error='Please enter your email address')
        
        # Check if user exists
        if not check_user_exists(email):
            return render_template('forget_password.html', error='Account not exist')
        
        # In a real application, you would send a password reset email here
        # For now, we'll just show a success message
        return render_template('forget_password.html', success='Password reset link has been sent to your email address.')
    
    return render_template('forget_password.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    critical_count = get_critical_equipment_count()
    technician_util = get_technician_utilization()
    pending_count, overdue_count = get_open_requests()
    requests = get_maintenance_requests()
    
    return render_template(
        'dashboard.html',
        user=session.get('email'),
        critical_count=critical_count,
        technician_util=technician_util,
        pending_count=pending_count,
        overdue_count=overdue_count,
        requests=requests
    )

@app.route('/maintenance')
def maintenance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session.get('email'), 
                         critical_count=0, technician_util=0, pending_count=0, 
                         overdue_count=0, requests=[])

@app.route('/maintenance-calendar')
def maintenance_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session.get('email'),
                         critical_count=0, technician_util=0, pending_count=0,
                         overdue_count=0, requests=[])

@app.route('/equipment')
def equipment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session.get('email'),
                         critical_count=get_critical_equipment_count(),
                         technician_util=0, pending_count=0,
                         overdue_count=0, requests=[])

@app.route('/reporting')
def reporting():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session.get('email'),
                         critical_count=0, technician_util=get_technician_utilization(),
                         pending_count=0, overdue_count=0, requests=[])

@app.route('/teams')
def teams():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    pending_count, overdue_count = get_open_requests()
    return render_template('dashboard.html', user=session.get('email'),
                         critical_count=0, technician_util=0,
                         pending_count=pending_count, overdue_count=overdue_count,
                         requests=[])

@app.route('/health')
def health():
    return {'status': 'healthy'}

def validate_password(password):
    """Validate password according to requirements"""
    errors = []
    
    # Check for lowercase
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')
    
    # Check for uppercase
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')
    
    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Password must contain at least one special character')
    
    # Check length
    if len(password) <= 8:
        errors.append('Password must be more than 8 characters')
    
    return '. '.join(errors) if errors else None

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

