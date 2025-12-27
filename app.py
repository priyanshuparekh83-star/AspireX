from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import re
from database import (
    init_db, init_auth_db, init_equipment_db, init_requests_db,
    create_user, check_user_exists, verify_credentials, get_user_by_email,
    get_critical_equipment_count, get_technician_utilization, get_open_requests, get_maintenance_requests,
    get_all_equipment, get_equipment_by_id, create_equipment, update_equipment, delete_equipment,
    create_maintenance_request, update_request_status, get_dashboard_stats,
    get_user_signups, get_all_users, get_maintenance_requests_simple,
    # New requests database functions
    create_maintenance_request_new, get_maintenance_requests_new, get_maintenance_requests_simple_new,
    update_request_status_new, get_dashboard_stats_new,
    get_maintenance_request_by_id, update_maintenance_request, delete_maintenance_request,
    get_worksheet_comments, add_worksheet_comment,
    # Work centers and equipment categories
    get_all_work_centers, create_work_center, get_work_center_by_id, update_work_center, delete_work_center,
    get_all_equipment_categories, create_equipment_category, get_equipment_category_by_id, 
    update_equipment_category, delete_equipment_category
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production

# Initialize database on startup
init_db()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            return render_template('auth.html', tab='signin', error='Please fill in all fields')
        
        # Check if user exists
        if not check_user_exists(email):
            return render_template('auth.html', tab='signin', error='Account not exist')
        
        # Verify credentials
        is_valid, user = verify_credentials(email, password)
        
        if is_valid:
            session['user_id'] = user[0]
            session['email'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            return render_template('auth.html', tab='signin', error='Invalid Password')
    
    return render_template('auth.html', tab='signin')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not email or not password or not confirm_password or not full_name:
            return render_template('auth.html', tab='signup', error='Please fill in all fields')
        
        # Check if email already exists
        if check_user_exists(email):
            return render_template('auth.html', tab='signup', error='Email already exists. Please use a different email.')
        
        # Validate password requirements
        password_errors = validate_password(password)
        if password_errors:
            return render_template('auth.html', tab='signup', error=password_errors)
        
        # Check if passwords match
        if password != confirm_password:
            return render_template('auth.html', tab='signup', error='Passwords do not match')
        
        # Create user
        success, message = create_user(email, password)
        
        if success:
            # Create profile
            import sqlite3
            conn = sqlite3.connect('equipment.db')
            cursor = conn.cursor()
            # Get the newly created user ID
            is_valid, user_data = verify_credentials(email, password)
            if is_valid:
                user_id = user_data[0]
                cursor.execute('INSERT INTO profiles (user_id, full_name) VALUES (?, ?)', (user_id, full_name))
                conn.commit()
            conn.close()
            
            return render_template('auth.html', tab='signup', success='Account created successfully! You can now sign in.')
        else:
            return render_template('auth.html', tab='signup', error=message)
    
    return render_template('auth.html', tab='signup')

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
    
    stats = get_dashboard_stats_new()
    equipment = get_all_equipment()
    work_centers = get_all_work_centers()
    requests = get_maintenance_requests_simple_new()
    all_requests = get_maintenance_requests_new()
    
    critical_count = get_critical_equipment_count()
    technician_util = get_technician_utilization()
    
    # Count requests by status from requests database
    new_count = len([r for r in all_requests if r[7] == 'New'])
    in_progress_count = len([r for r in all_requests if r[7] == 'In Progress'])
    blocked_count = len([r for r in all_requests if r[7] == 'Blocked'])
    ready_count = len([r for r in all_requests if r[7] == 'Ready for next stage'])
    completed_count = len([r for r in all_requests if r[7] == 'Repaired'])
    scrap_count = len([r for r in all_requests if r[7] == 'Scrap'])
    total_requests = len(all_requests)
    
    pending_count = new_count + in_progress_count
    
    # Get overdue count from stats (calculated in database)
    overdue_count = stats.get('overdue', 0)
    
    # Calculate progress bar widths - more meaningful calculations
    # Critical equipment: show as percentage of total equipment (if we have equipment data)
    total_equipment = stats.get('total_equipment', 0)
    critical_progress = min((critical_count / total_equipment * 100) if total_equipment > 0 else (critical_count * 20), 100) if critical_count > 0 else 0
    
    # Open requests: show as percentage of total requests
    requests_progress = min((pending_count / total_requests * 100) if total_requests > 0 else 0, 100) if pending_count > 0 else 0
    
    # Calculate progress percentages for request status cards (as % of total requests)
    new_progress = min((new_count / total_requests * 100) if total_requests > 0 else 0, 100)
    in_progress_progress = min((in_progress_count / total_requests * 100) if total_requests > 0 else 0, 100)
    completed_progress = min((completed_count / total_requests * 100) if total_requests > 0 else 0, 100)
    
    return render_template(
        'dashboard.html',
        user=session.get('email'),
        critical_count=critical_count,
        technician_util=technician_util,
        pending_count=pending_count,
        overdue_count=overdue_count,
            requests=requests,
            equipment=equipment,
            work_centers=work_centers,
            critical_progress=critical_progress,
        requests_progress=requests_progress,
        # New detailed request stats
        new_count=new_count,
        in_progress_count=in_progress_count,
        blocked_count=blocked_count,
        ready_count=ready_count,
        completed_count=completed_count,
        scrap_count=scrap_count,
        total_requests=total_requests,
        new_progress=new_progress,
        in_progress_progress=in_progress_progress,
        completed_progress=completed_progress,
        stats=stats
    )

@app.route('/maintenance')
def maintenance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    equipment = get_all_equipment()
    work_centers = get_all_work_centers()
    all_requests = get_maintenance_requests_new()
    stats = get_dashboard_stats_new()
    
    # Count requests by status
    new_count = len([r for r in all_requests if r[7] == 'New'])
    in_progress_count = len([r for r in all_requests if r[7] == 'In Progress'])
    blocked_count = len([r for r in all_requests if r[7] == 'Blocked'])
    ready_count = len([r for r in all_requests if r[7] == 'Ready for next stage'])
    completed_count = len([r for r in all_requests if r[7] == 'Repaired'])
    scrap_count = len([r for r in all_requests if r[7] == 'Scrap'])
    total_requests = len(all_requests)
    
    # Calculate progress percentages for visual indicators
    new_progress = min((new_count / total_requests * 100) if total_requests > 0 else 0, 100)
    in_progress_progress = min((in_progress_count / total_requests * 100) if total_requests > 0 else 0, 100)
    completed_progress = min((completed_count / total_requests * 100) if total_requests > 0 else 0, 100)
    
    return render_template('maintenance.html', 
                         active_page='maintenance',
                         user=session.get('email'),
                         equipment=equipment,
                         work_centers=work_centers,
                         requests=all_requests,
                         new_count=new_count,
                         in_progress_count=in_progress_count,
                         blocked_count=blocked_count,
                         ready_count=ready_count,
                         completed_count=completed_count,
                         scrap_count=scrap_count,
                         total_requests=total_requests,
                         new_progress=new_progress,
                         in_progress_progress=in_progress_progress,
                         completed_progress=completed_progress,
                         stats=stats)

@app.route('/maintenance-calendar')
def maintenance_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all maintenance requests with scheduled dates
    all_requests = get_maintenance_requests_new()
    
    # Debug: Print request structure
    print(f"Total requests fetched: {len(all_requests)}")
    if all_requests:
        print(f"First request length: {len(all_requests[0])}")
        print(f"First request: {all_requests[0]}")
    
    # Filter requests that have scheduled_date and format them properly
    # Column order: id(0), subject(1), employee(2), technician(3), category(4), stage(5), 
    # company(6), status(7), request_type(8), priority(9), description(10), 
    # scheduled_date(11), due_date(12), equipment_id(13), team(14), request_date(15), 
    # duration(16), created_at(17), updated_at(18), equipment_name(19)
    scheduled_requests = []
    for req in all_requests:
        # Check if request has enough columns and scheduled_date exists
        if len(req) > 11:
            scheduled_date = req[11] if len(req) > 11 else None
            created_at = req[17] if len(req) > 17 else None  # created_at at index 17
            
            # Only process if scheduled_date is not None and not empty
            if scheduled_date:
                scheduled_date_str = str(scheduled_date).strip()
                
                # Skip if empty string
                if scheduled_date_str and scheduled_date_str.lower() != 'none':
                    # If it's just a date (YYYY-MM-DD), use time from created_at
                    if len(scheduled_date_str) == 10 and ' ' not in scheduled_date_str and 'T' not in scheduled_date_str:
                        # Extract time from created_at if available
                        if created_at:
                            created_at_str = str(created_at).strip()
                            # Extract time from created_at (format: YYYY-MM-DD HH:MM:SS)
                            if ' ' in created_at_str:
                                time_part = created_at_str.split(' ')[1]
                                # Take only HH:MM:SS part
                                if ':' in time_part:
                                    scheduled_date_str = f"{scheduled_date_str} {time_part.split('.')[0]}"  # Remove microseconds if present
                                else:
                                    scheduled_date_str = f"{scheduled_date_str} 09:00:00"
                            elif 'T' in created_at_str:
                                time_part = created_at_str.split('T')[1].split('.')[0]  # Remove microseconds
                                scheduled_date_str = f"{scheduled_date_str} {time_part}"
                            else:
                                scheduled_date_str = f"{scheduled_date_str} 09:00:00"  # Fallback
                        else:
                            scheduled_date_str = f"{scheduled_date_str} 09:00:00"  # Default if no created_at
                    # Convert T separator to space for consistency
                    elif 'T' in scheduled_date_str:
                        scheduled_date_str = scheduled_date_str.replace('T', ' ')
                    
                    scheduled_requests.append({
                        'id': req[0],
                        'subject': req[1] if len(req) > 1 else 'No Subject',
                        'employee': req[2] if len(req) > 2 else '',
                        'technician': req[3] if len(req) > 3 else '',
                        'scheduled_date': scheduled_date_str,
                        'due_date': req[12] if len(req) > 12 else None,
                        'status': req[7] if len(req) > 7 else 'New',
                        'priority': req[9] if len(req) > 9 else 'Medium',
                        'equipment_name': req[19] if len(req) > 19 else None,
                        'created_at': str(created_at) if created_at else None
                    })
    
    print(f"Scheduled requests found: {len(scheduled_requests)}")
    for sr in scheduled_requests:
        print(f"  - ID: {sr['id']}, Subject: {sr['subject']}, Date: {sr['scheduled_date']}")
    
    # Get current date info
    from datetime import datetime, timedelta
    today = datetime.now()
    current_week_start = today - timedelta(days=today.weekday())
    
    return render_template('calendar.html', 
                         active_page='maintenance-calendar',
                         user=session.get('email'),
                         scheduled_requests=scheduled_requests,
                         current_date=today.strftime('%Y-%m-%d'),
                         current_time=today.strftime('%H:%M'),
                         week_start=current_week_start.strftime('%Y-%m-%d'))


@app.route('/create-request', methods=['POST'])
def create_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    subject = request.form.get('subject', '').strip()
    maintenance_for = request.form.get('maintenance_for', 'Equipment').strip()
    equipment_id = request.form.get('equipment_id', '').strip() or None
    work_center_id = request.form.get('work_center_id', '').strip() or None
    request_type = request.form.get('request_type', 'Corrective')
    priority = request.form.get('priority', 'Medium')
    description = request.form.get('description', '').strip()
    scheduled_date = request.form.get('scheduled_date') or None
    due_date = request.form.get('due_date') or None
    team = request.form.get('team', '').strip() or None
    technician = request.form.get('technician', '').strip() or None
    category = request.form.get('category', '').strip() or None
    request_date = request.form.get('request_date') or None
    duration = request.form.get('duration', '').strip() or None
    company = request.form.get('company', 'My company').strip()
    notes = request.form.get('notes', '').strip() or None
    instructions = request.form.get('instructions', '').strip() or None
    
    if not subject:
        flash('Subject is required', 'error')
        return redirect(url_for('dashboard'))
    
    # Validate that either equipment_id or work_center_id is provided based on maintenance_for
    if maintenance_for == 'Equipment' and not equipment_id:
        flash('Please select an equipment', 'error')
        return redirect(url_for('dashboard'))
    elif maintenance_for == 'Work Center':
        if not work_center_id:
            flash('Please select a work center', 'error')
            return redirect(url_for('dashboard'))
        # Check if work center exists
        work_centers_list = get_all_work_centers()
        if not work_centers_list:
            flash('No work centers available. Please create a work center first.', 'error')
            return redirect(url_for('dashboard'))
    
    employee = session.get('email', 'Unknown')
    success, message = create_maintenance_request_new(
        subject, employee, equipment_id, request_type, priority, 
        description, scheduled_date, due_date, company, team, 
        technician, category, request_date, duration,
        work_center_id=work_center_id,
        maintenance_for=maintenance_for,
        notes=notes,
        instructions=instructions
    )
    
    if success:
        flash('Request created successfully!', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/update-request-status', methods=['POST'])
def update_request():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401
    
    data = request.get_json()
    request_id = data.get('request_id')
    status = data.get('status')
    
    if update_request_status_new(request_id, status):
        return jsonify({'success': True}), 200
    return jsonify({'success': False}), 400

@app.route('/view-request/<int:request_id>')
def view_request(request_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        request_data = get_maintenance_request_by_id(request_id)
        if not request_data:
            return jsonify({'success': False, 'message': 'Request not found'}), 404
        
        # Convert tuple to dictionary for JSON response
        # Database has 19 columns (0-18), equipment_name is appended at index 19
        request_dict = {
            'id': request_data[0] if len(request_data) > 0 else None,
            'subject': request_data[1] if len(request_data) > 1 else None,
            'employee': request_data[2] if len(request_data) > 2 else None,
            'technician': request_data[3] if len(request_data) > 3 else None,
            'category': request_data[4] if len(request_data) > 4 else None,
            'stage': request_data[5] if len(request_data) > 5 else None,
            'company': request_data[6] if len(request_data) > 6 else None,
            'status': request_data[7] if len(request_data) > 7 else None,
            'request_type': request_data[8] if len(request_data) > 8 else None,
            'priority': request_data[9] if len(request_data) > 9 else None,
            'description': request_data[10] if len(request_data) > 10 else None,
            'scheduled_date': request_data[11] if len(request_data) > 11 else None,
            'due_date': request_data[12] if len(request_data) > 12 else None,
            'equipment_id': request_data[13] if len(request_data) > 13 else None,
            'team': request_data[14] if len(request_data) > 14 else None,
            'request_date': request_data[15] if len(request_data) > 15 else None,
            'duration': request_data[16] if len(request_data) > 16 else None,
            'created_at': request_data[17] if len(request_data) > 17 else None,
            'updated_at': request_data[18] if len(request_data) > 18 else None,
            'equipment_name': request_data[19] if len(request_data) > 19 else None
        }
        
        return jsonify({'success': True, 'request': request_dict})
    except Exception as e:
        import traceback
        print(f"Error in view_request: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/update-request', methods=['POST'])
def update_request_full():
    if 'user_id' not in session:
        flash('Unauthorized', 'error')
        return redirect(url_for('login'))
    
    request_id = request.form.get('request_id')
    if not request_id:
        flash('Request ID is required', 'error')
        return redirect(url_for('dashboard'))
    
    subject = request.form.get('subject', '').strip() or None
    employee = request.form.get('employee', '').strip() or None
    equipment_id = request.form.get('equipment_id', '').strip() or None
    request_type = request.form.get('request_type') or None
    priority = request.form.get('priority') or None
    description = request.form.get('description', '').strip() or None
    scheduled_date = request.form.get('scheduled_date') or None
    due_date = request.form.get('due_date') or None
    company = request.form.get('company', '').strip() or None
    team = request.form.get('team', '').strip() or None
    technician = request.form.get('technician', '').strip() or None
    category = request.form.get('category', '').strip() or None
    request_date = request.form.get('request_date') or None
    duration = request.form.get('duration', '').strip() or None
    status = request.form.get('status') or None
    
    success, message = update_maintenance_request(
        int(request_id),
        subject=subject,
        employee=employee,
        equipment_id=int(equipment_id) if equipment_id else None,
        request_type=request_type,
        priority=priority,
        description=description,
        scheduled_date=scheduled_date,
        due_date=due_date,
        company=company,
        team=team,
        technician=technician,
        category=category,
        request_date=request_date,
        duration=duration,
        status=status
    )
    
    if success:
        flash('Request updated successfully!', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/delete-request/<int:request_id>', methods=['DELETE'])
def delete_request(request_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    success, message = delete_maintenance_request(request_id)
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/users')
def users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    signups = get_user_signups()
    users_list = get_all_users()
    
    return render_template('users.html', active_page='users', user=session.get('email'), signups=signups, users=users_list)

@app.route('/equipment')
def equipment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    equipment_list = get_all_equipment()
    categories = get_all_equipment_categories()
    work_centers = get_all_work_centers()
    return render_template('equipment.html', active_page='equipment', user=session.get('email'), 
                         equipment=equipment_list, categories=categories, work_centers=work_centers)

@app.route('/equipment/<int:equipment_id>')
def equipment_detail(equipment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    equipment_data = get_equipment_by_id(equipment_id)
    if not equipment_data:
        flash('Equipment not found', 'error')
        return redirect(url_for('equipment'))
    
    categories = get_all_equipment_categories()
    work_centers = get_all_work_centers()
    # Get maintenance requests for this equipment
    all_requests = get_maintenance_requests_new()
    equipment_requests = [r for r in all_requests if len(r) > 13 and r[13] and int(r[13]) == equipment_id]
    
    return render_template('equipment_detail.html', active_page='equipment', 
                         user=session.get('email'), equipment=equipment_data,
                         categories=categories, work_centers=work_centers,
                         requests=equipment_requests)

@app.route('/create-equipment', methods=['POST'])
def create_equipment_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    success, result = create_equipment(
        name=request.form.get('name'),
        employee=request.form.get('employee'),
        department=request.form.get('department'),
        serial_number=request.form.get('serial_number'),
        technician=request.form.get('technician'),
        equipment_category_id=request.form.get('equipment_category_id') or None,
        company=request.form.get('company'),
        used_by=request.form.get('used_by'),
        maintenance_team=request.form.get('maintenance_team'),
        assigned_date=request.form.get('assigned_date'),
        description=request.form.get('description'),
        scrap_date=request.form.get('scrap_date'),
        used_in_location=request.form.get('used_in_location'),
        work_center_id=request.form.get('work_center_id') or None,
        health_percentage=int(request.form.get('health_percentage', 100)),
        status=request.form.get('status', 'active')
    )
    
    if success:
        flash('Equipment created successfully', 'success')
        return redirect(url_for('equipment'))
    else:
        flash(f'Error: {result}', 'error')
        return redirect(url_for('equipment'))

@app.route('/update-equipment', methods=['POST'])
def update_equipment_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    equipment_id = request.form.get('equipment_id')
    success, result = update_equipment(
        equipment_id=int(equipment_id),
        name=request.form.get('name'),
        employee=request.form.get('employee'),
        department=request.form.get('department'),
        serial_number=request.form.get('serial_number'),
        technician=request.form.get('technician'),
        equipment_category_id=request.form.get('equipment_category_id') or None,
        company=request.form.get('company'),
        used_by=request.form.get('used_by'),
        maintenance_team=request.form.get('maintenance_team'),
        assigned_date=request.form.get('assigned_date'),
        description=request.form.get('description'),
        scrap_date=request.form.get('scrap_date'),
        used_in_location=request.form.get('used_in_location'),
        work_center_id=request.form.get('work_center_id') or None,
        health_percentage=int(request.form.get('health_percentage', 100)),
        status=request.form.get('status', 'active')
    )
    
    if success:
        flash('Equipment updated successfully', 'success')
        return redirect(url_for('equipment_detail', equipment_id=equipment_id))
    else:
        flash(f'Error: {result}', 'error')
        return redirect(url_for('equipment_detail', equipment_id=equipment_id))

@app.route('/delete-equipment/<int:equipment_id>', methods=['POST'])
def delete_equipment_route(equipment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    success, result = delete_equipment(equipment_id)
    if success:
        flash('Equipment deleted successfully', 'success')
    else:
        flash(f'Error: {result}', 'error')
    
    return redirect(url_for('equipment'))

@app.route('/requests')
def requests_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_requests = get_maintenance_requests_new()
    return render_template('requests.html', active_page='requests', user=session.get('email'), requests=all_requests)

@app.route('/teams')
def teams():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('teams.html', active_page='teams', user=session.get('email'))

@app.route('/reporting')
def reporting():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all requests for reporting
    all_requests = get_maintenance_requests_new()
    stats = get_dashboard_stats_new()
    equipment = get_all_equipment()
    
    # Count requests by status
    new_count = len([r for r in all_requests if r[7] == 'New'])
    in_progress_count = len([r for r in all_requests if r[7] == 'In Progress'])
    blocked_count = len([r for r in all_requests if r[7] == 'Blocked'])
    ready_count = len([r for r in all_requests if r[7] == 'Ready for next stage'])
    completed_count = len([r for r in all_requests if r[7] == 'Repaired'])
    scrap_count = len([r for r in all_requests if r[7] == 'Scrap'])
    total_requests = len(all_requests)
    
    # Get overdue count
    overdue_count = stats.get('overdue', 0)
    
    # Get equipment stats
    total_equipment = len(equipment)
    critical_count = get_critical_equipment_count()
    
    return render_template('reporting.html', 
                         active_page='reporting', 
                         user=session.get('email'),
                         total_requests=total_requests,
                         new_count=new_count,
                         in_progress_count=in_progress_count,
                         blocked_count=blocked_count,
                         ready_count=ready_count,
                         completed_count=completed_count,
                         scrap_count=scrap_count,
                         overdue_count=overdue_count,
                         total_equipment=total_equipment,
                         critical_count=critical_count)

@app.route('/generate-report', methods=['POST'])
def generate_report():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    report_type = data.get('report_type')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    status_filter = data.get('status_filter')
    export_format = data.get('export_format', 'html')
    
    try:
        if report_type == 'maintenance_requests':
            return generate_maintenance_requests_report(start_date, end_date, status_filter, export_format)
        elif report_type == 'equipment_status':
            return generate_equipment_status_report(export_format)
        elif report_type == 'status_summary':
            return generate_status_summary_report(export_format)
        elif report_type == 'overdue_requests':
            return generate_overdue_requests_report(start_date, end_date, export_format)
        elif report_type == 'technician_performance':
            return generate_technician_performance_report(start_date, end_date, export_format)
        elif report_type == 'work_centers':
            return generate_work_centers_report(export_format)
        elif report_type == 'equipment_categories':
            return generate_equipment_categories_report(export_format)
        else:
            return jsonify({'success': False, 'message': 'Invalid report type'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def generate_maintenance_requests_report(start_date, end_date, status_filter, export_format):
    """Generate maintenance requests report"""
    all_requests = get_maintenance_requests_new()
    
    # Filter by date range
    filtered_requests = all_requests
    if start_date or end_date:
        filtered_requests = []
        for req in all_requests:
            req_date = req[15] if len(req) > 15 else None  # request_date at index 15
            if req_date:
                if start_date and req_date < start_date:
                    continue
                if end_date and req_date > end_date:
                    continue
            filtered_requests.append(req)
    
    # Filter by status
    if status_filter:
        filtered_requests = [r for r in filtered_requests if r[7] == status_filter]
    
    # Generate HTML content
    html_content = f'''
    <div style="padding: 20px;">
        <h3 style="color: #333; margin-bottom: 20px;">Maintenance Requests Report</h3>
        <p style="color: #666; margin-bottom: 20px;">
            <strong>Date Range:</strong> {start_date or 'All'} to {end_date or 'All'}<br>
            <strong>Status Filter:</strong> {status_filter or 'All'}<br>
            <strong>Total Records:</strong> {len(filtered_requests)}
        </p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">ID</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Subject</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Employee</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Technician</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Status</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Priority</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Request Date</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Scheduled Date</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    table_data = []
    for req in filtered_requests:
        table_data.append({
            'ID': req[0],
            'Subject': req[1],
            'Employee': req[2],
            'Technician': req[3] or 'Unassigned',
            'Status': req[7],
            'Priority': req[9],
            'Request Date': req[15] if len(req) > 15 else 'N/A',
            'Scheduled Date': req[11] if len(req) > 11 and req[11] else 'N/A'
        })
        
        html_content += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;">{req[0]}</td>
                    <td style="padding: 12px;">{req[1]}</td>
                    <td style="padding: 12px;">{req[2]}</td>
                    <td style="padding: 12px;">{req[3] or 'Unassigned'}</td>
                    <td style="padding: 12px;">{req[7]}</td>
                    <td style="padding: 12px;">{req[9]}</td>
                    <td style="padding: 12px;">{req[15] if len(req) > 15 else 'N/A'}</td>
                    <td style="padding: 12px;">{req[11] if len(req) > 11 and req[11] else 'N/A'}</td>
                </tr>
        '''
    
    html_content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return jsonify({
        'success': True,
        'report_title': 'Maintenance Requests Report',
        'html_content': html_content,
        'table_data': table_data,
        'csv_content': generate_csv_from_data(table_data)
    })

def generate_equipment_status_report(export_format):
    """Generate equipment status report"""
    equipment = get_all_equipment()
    
    html_content = f'''
    <div style="padding: 20px;">
        <h3 style="color: #333; margin-bottom: 20px;">Equipment Status Report</h3>
        <p style="color: #666; margin-bottom: 20px;"><strong>Total Equipment:</strong> {len(equipment)}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">ID</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Name</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Health</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Status</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Created</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    table_data = []
    for eq in equipment:
        health = eq[2] if len(eq) > 2 else 100
        status = eq[3] if len(eq) > 3 else 'active'
        table_data.append({
            'ID': eq[0],
            'Name': eq[1],
            'Health': f'{health}%',
            'Status': status,
            'Created': eq[4] if len(eq) > 4 else 'N/A'
        })
        
        health_color = '#e74c3c' if health < 30 else '#f39c12' if health < 60 else '#2ecc71'
        html_content += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;">{eq[0]}</td>
                    <td style="padding: 12px;">{eq[1]}</td>
                    <td style="padding: 12px; color: {health_color}; font-weight: 600;">{health}%</td>
                    <td style="padding: 12px;">{status}</td>
                    <td style="padding: 12px;">{eq[4] if len(eq) > 4 else 'N/A'}</td>
                </tr>
        '''
    
    html_content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return jsonify({
        'success': True,
        'report_title': 'Equipment Status Report',
        'html_content': html_content,
        'table_data': table_data,
        'csv_content': generate_csv_from_data(table_data)
    })

def generate_status_summary_report(export_format):
    """Generate status summary report"""
    all_requests = get_maintenance_requests_new()
    
    # Count by status
    status_counts = {}
    for req in all_requests:
        status = req[7] if len(req) > 7 else 'Unknown'
        status_counts[status] = status_counts.get(status, 0) + 1
    
    total = len(all_requests)
    
    html_content = f'''
    <div style="padding: 20px;">
        <h3 style="color: #333; margin-bottom: 20px;">Status Summary Report</h3>
        <p style="color: #666; margin-bottom: 20px;"><strong>Total Requests:</strong> {total}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Status</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Count</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Percentage</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    table_data = []
    for status, count in sorted(status_counts.items()):
        percentage = (count / total * 100) if total > 0 else 0
        table_data.append({
            'Status': status,
            'Count': count,
            'Percentage': f'{percentage:.1f}%'
        })
        
        html_content += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;"><strong>{status}</strong></td>
                    <td style="padding: 12px;">{count}</td>
                    <td style="padding: 12px;">{percentage:.1f}%</td>
                </tr>
        '''
    
    html_content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return jsonify({
        'success': True,
        'report_title': 'Status Summary Report',
        'html_content': html_content,
        'table_data': table_data,
        'csv_content': generate_csv_from_data(table_data)
    })

def generate_overdue_requests_report(start_date, end_date, export_format):
    """Generate overdue requests report"""
    all_requests = get_maintenance_requests_new()
    from datetime import datetime
    
    overdue_requests = []
    today = datetime.now().date()
    
    for req in all_requests:
        due_date_str = req[12] if len(req) > 12 else None  # due_date at index 12
        status = req[7] if len(req) > 7 else 'New'
        
        if due_date_str and status in ['New', 'In Progress', 'Blocked', 'Ready for next stage']:
            try:
                due_date = datetime.strptime(str(due_date_str), '%Y-%m-%d').date()
                if due_date < today:
                    overdue_requests.append(req)
            except:
                pass
    
    html_content = f'''
    <div style="padding: 20px;">
        <h3 style="color: #333; margin-bottom: 20px;">Overdue Requests Report</h3>
        <p style="color: #666; margin-bottom: 20px;"><strong>Total Overdue:</strong> {len(overdue_requests)}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">ID</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Subject</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Employee</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Due Date</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Status</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Priority</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    table_data = []
    for req in overdue_requests:
        table_data.append({
            'ID': req[0],
            'Subject': req[1],
            'Employee': req[2],
            'Due Date': req[12] if len(req) > 12 else 'N/A',
            'Status': req[7],
            'Priority': req[9]
        })
        
        html_content += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;">{req[0]}</td>
                    <td style="padding: 12px;">{req[1]}</td>
                    <td style="padding: 12px;">{req[2]}</td>
                    <td style="padding: 12px; color: #e74c3c; font-weight: 600;">{req[12] if len(req) > 12 else 'N/A'}</td>
                    <td style="padding: 12px;">{req[7]}</td>
                    <td style="padding: 12px;">{req[9]}</td>
                </tr>
        '''
    
    html_content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return jsonify({
        'success': True,
        'report_title': 'Overdue Requests Report',
        'html_content': html_content,
        'table_data': table_data,
        'csv_content': generate_csv_from_data(table_data)
    })

def generate_technician_performance_report(start_date, end_date, export_format):
    """Generate technician performance report"""
    all_requests = get_maintenance_requests_new()
    
    # Group by technician
    technician_stats = {}
    for req in all_requests:
        technician = req[3] if len(req) > 3 and req[3] else 'Unassigned'
        status = req[7] if len(req) > 7 else 'New'
        
        if technician not in technician_stats:
            technician_stats[technician] = {
                'total': 0,
                'completed': 0,
                'in_progress': 0,
                'new': 0
            }
        
        technician_stats[technician]['total'] += 1
        if status == 'Repaired':
            technician_stats[technician]['completed'] += 1
        elif status == 'In Progress':
            technician_stats[technician]['in_progress'] += 1
        elif status == 'New':
            technician_stats[technician]['new'] += 1
    
    html_content = f'''
    <div style="padding: 20px;">
        <h3 style="color: #333; margin-bottom: 20px;">Technician Performance Report</h3>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Technician</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Total Requests</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Completed</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">In Progress</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">New</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Completion Rate</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    table_data = []
    for tech, stats in sorted(technician_stats.items()):
        completion_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        table_data.append({
            'Technician': tech,
            'Total Requests': stats['total'],
            'Completed': stats['completed'],
            'In Progress': stats['in_progress'],
            'New': stats['new'],
            'Completion Rate': f'{completion_rate:.1f}%'
        })
        
        html_content += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;"><strong>{tech}</strong></td>
                    <td style="padding: 12px;">{stats['total']}</td>
                    <td style="padding: 12px; color: #2ecc71;">{stats['completed']}</td>
                    <td style="padding: 12px; color: #f39c12;">{stats['in_progress']}</td>
                    <td style="padding: 12px; color: #3498db;">{stats['new']}</td>
                    <td style="padding: 12px; font-weight: 600;">{completion_rate:.1f}%</td>
                </tr>
        '''
    
    html_content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return jsonify({
        'success': True,
        'report_title': 'Technician Performance Report',
        'html_content': html_content,
        'table_data': table_data,
        'csv_content': generate_csv_from_data(table_data)
    })

def generate_work_centers_report(export_format):
    """Generate work centers report"""
    work_centers = get_all_work_centers()
    
    html_content = f'''
    <div style="padding: 20px;">
        <h3 style="color: #333; margin-bottom: 20px;">Work Centers Report</h3>
        <p style="color: #666; margin-bottom: 20px;"><strong>Total Work Centers:</strong> {len(work_centers)}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Name</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Code</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Cost per hour</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Capacity Time Efficiency</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">OEE Target</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Company</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    table_data = []
    for wc in work_centers:
        table_data.append({
            'Name': wc[1],
            'Code': wc[2] or '',
            'Cost per hour': wc[5] if wc[5] else 0,
            'Capacity Time Efficiency': wc[6] if wc[6] else 100,
            'OEE Target': wc[7] if wc[7] else 0,
            'Company': wc[8] or 'My company'
        })
        
        html_content += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;"><strong>{wc[1]}</strong></td>
                    <td style="padding: 12px;">{wc[2] or '-'}</td>
                    <td style="padding: 12px;">{wc[5] if wc[5] else 0:.2f}</td>
                    <td style="padding: 12px;">{wc[6] if wc[6] else 100:.2f}</td>
                    <td style="padding: 12px;">{wc[7] if wc[7] else 0:.2f}</td>
                    <td style="padding: 12px;">{wc[8] or 'My company'}</td>
                </tr>
        '''
    
    html_content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return jsonify({
        'success': True,
        'report_title': 'Work Centers Report',
        'html_content': html_content,
        'table_data': table_data,
        'csv_content': generate_csv_from_data(table_data)
    })

def generate_equipment_categories_report(export_format):
    """Generate equipment categories report"""
    categories = get_all_equipment_categories()
    
    html_content = f'''
    <div style="padding: 20px;">
        <h3 style="color: #333; margin-bottom: 20px;">Equipment Categories Report</h3>
        <p style="color: #666; margin-bottom: 20px;"><strong>Total Categories:</strong> {len(categories)}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #e0e0e0;">
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Name</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Responsible</th>
                    <th style="padding: 12px; text-align: left; font-weight: 600; color: #333;">Company</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    table_data = []
    for cat in categories:
        table_data.append({
            'Name': cat[1],
            'Responsible': cat[2] or '',
            'Company': cat[3] or 'My company'
        })
        
        html_content += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;"><strong>{cat[1]}</strong></td>
                    <td style="padding: 12px;">{cat[2] or '-'}</td>
                    <td style="padding: 12px;">{cat[3] or 'My company'}</td>
                </tr>
        '''
    
    html_content += '''
            </tbody>
        </table>
    </div>
    '''
    
    return jsonify({
        'success': True,
        'report_title': 'Equipment Categories Report',
        'html_content': html_content,
        'table_data': table_data,
        'csv_content': generate_csv_from_data(table_data)
    })

def generate_csv_from_data(table_data):
    """Generate CSV content from table data"""
    if not table_data:
        return ''
    
    # Header
    csv_lines = [','.join(table_data[0].keys())]
    
    # Rows
    for row in table_data:
        csv_lines.append(','.join([str(v) for v in row.values()]))
    
    return '\n'.join(csv_lines)

@app.route('/calendar')
def calendar_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all maintenance requests with scheduled dates
    all_requests = get_maintenance_requests_new()
    
    # Filter requests that have scheduled_date
    scheduled_requests = []
    for req in all_requests:
        if len(req) > 11 and req[11]:  # scheduled_date at index 11
            scheduled_requests.append({
                'id': req[0],
                'subject': req[1],
                'employee': req[2],
                'technician': req[3],
                'scheduled_date': req[11],
                'due_date': req[12] if len(req) > 12 else None,
                'status': req[7] if len(req) > 7 else 'New',
                'priority': req[9] if len(req) > 9 else 'Medium',
                'equipment_name': req[19] if len(req) > 19 else None
            })
    
    # Get current date info
    from datetime import datetime, timedelta
    today = datetime.now()
    current_week_start = today - timedelta(days=today.weekday())
    
    return render_template('calendar.html', 
                         active_page='calendar',
                         user=session.get('email'),
                         scheduled_requests=scheduled_requests,
                         current_date=today.strftime('%Y-%m-%d'),
                         current_time=today.strftime('%H:%M'),
                         week_start=current_week_start.strftime('%Y-%m-%d'))

@app.route('/settings')
def settings_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('settings.html', active_page='settings', user=session.get('email'))

@app.route('/get-worksheet-comments/<int:request_id>')
def get_worksheet_comments_route(request_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    comments = get_worksheet_comments(request_id)
    return jsonify({'success': True, 'comments': comments})

@app.route('/add-worksheet-comment', methods=['POST'])
def add_worksheet_comment_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    request_id = data.get('request_id')
    comment = data.get('comment', '').strip()
    
    if not comment:
        return jsonify({'success': False, 'message': 'Comment cannot be empty'}), 400
    
    user = session.get('email', 'Unknown')
    success, message = add_worksheet_comment(request_id, user, comment)
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/work-centers')
def work_centers():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    work_centers_list = get_all_work_centers()
    return render_template('work_centers.html',
                         active_page='work-centers',
                         user=session.get('email'),
                         work_centers=work_centers_list)

@app.route('/equipment-categories')
def equipment_categories():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    categories = get_all_equipment_categories()
    return render_template('equipment_categories.html',
                         active_page='equipment-categories',
                         user=session.get('email'),
                         categories=categories)

@app.route('/create-work-center', methods=['POST'])
def create_work_center_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    name = request.form.get('name', '').strip()
    code = request.form.get('code', '').strip() or None
    tag = request.form.get('tag', '').strip() or None
    alternative_workcenters = request.form.get('alternative_workcenters', '').strip() or None
    cost_per_hour = float(request.form.get('cost_per_hour', 0) or 0)
    capacity_time_efficiency = float(request.form.get('capacity_time_efficiency', 100) or 100)
    oee_target = float(request.form.get('oee_target', 0) or 0)
    company = request.form.get('company', 'My company').strip()
    
    if not name:
        flash('Work center name is required', 'error')
        return redirect(url_for('work_centers'))
    
    success, message = create_work_center(name, code, tag, alternative_workcenters, cost_per_hour, capacity_time_efficiency, oee_target, company)
    
    if success:
        flash('Work center created successfully!', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('work_centers'))

@app.route('/create-equipment-category', methods=['POST'])
def create_equipment_category_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    name = request.form.get('name', '').strip()
    responsible = request.form.get('responsible', '').strip() or None
    company = request.form.get('company', 'My company').strip()
    
    if not name:
        flash('Category name is required', 'error')
        return redirect(url_for('equipment_categories'))
    
    success, message = create_equipment_category(name, responsible, company)
    
    if success:
        flash('Equipment category created successfully!', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('equipment_categories'))

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

