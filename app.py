from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
from functools import wraps
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/sala'
db = SQLAlchemy(app)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')
print(app.secret_key)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Disponível')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(255))
    booked_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    room = db.relationship('Room', backref=db.backref('meetings', lazy=True))

@app.route('/')
def rooms():
    rooms = Room.query.all()
    return render_template('main.html', rooms=rooms)

@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    
    name = data.get('name')
    description = data.get('description')
    capacity = data.get('capacity')
    
    if not name or not capacity:
        return jsonify({'error': 'Name and capacity are required'}), 400

    new_room = Room(
        name=name,
        description=description,
        capacity=capacity
    )

    db.session.add(new_room)
    db.session.commit()
    
    return jsonify({'message': 'Room created successfully', 'room_id': new_room.id}), 201

@app.route('/room/<int:room_id>/schedule', methods=['GET', 'POST'])
def room_schedule(room_id):
    room = Room.query.get_or_404(room_id)

    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = (datetime.combine(datetime.today(), start_time) + timedelta(hours=1)).time()
        purpose = data.get('purpose')

        user = User.query.filter_by(username=username).first()

        # Simple password check
        if not user or user.password != password:
            return jsonify({"error": "Usuário ou senha incorretos!"}), 401

        # Ensure the meeting is within working hours
        if start_time < time(8, 0) or end_time > time(18, 0):
            return jsonify({"error": "Meetings can only be scheduled between 8 AM and 6 PM"}), 400

        # Check for conflicts
        conflicts = Meeting.query.filter_by(room_id=room_id).filter(
            Meeting.start_time < end_time,
            Meeting.end_time > start_time
        ).all()

        if conflicts:
            return jsonify({"error": "The room is already booked for the requested time"}), 409

        # Create and commit the new meeting
        new_meeting = Meeting(
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            booked_by=user.username
        )

        db.session.add(new_meeting)
        db.session.commit()

        return jsonify({"message": "Meeting scheduled successfully", "meeting_id": new_meeting.id}), 201

    # Handle the GET request to view the schedule
    meetings = Meeting.query.filter_by(room_id=room.id).all()

    schedule = []
    start_hour = 8
    end_hour = 18

    for hour in range(start_hour, end_hour):
        time_slot = {
            "time": f"{hour}:00",
            "status": "Disponível",
            "meeting": None
        }
        for meeting in meetings:
            if time(hour, 0) <= meeting.start_time < time(hour + 1, 0):
                time_slot["status"] = "Occupied"
                time_slot["meeting"] = {
                    "purpose": meeting.purpose,
                    "booked_by": meeting.booked_by,
                    "start_time": meeting.start_time.strftime("%H:%M"),
                    "end_time": meeting.end_time.strftime("%H:%M"),
                }
                break
        schedule.append(time_slot)

    return render_template('room.html', room=room, schedule=schedule)

def is_admin():
    return session.get('is_admin', False)

# Admin login page
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # Check for simple password match without hashing
        if user and user.password == password and user.is_admin:
            session['admin_logged_in'] = True
            session['is_admin'] = user.is_admin
            return redirect(url_for('admin_users'))
        
        flash('Usuário e senha incorretos ou usuário não permitido!')  # Flash message if login fails or user is not an admin
        return redirect(url_for('admin_login'))
        
    return render_template('admin_login.html')

# Admin users management page
@app.route('/admin/users')
def admin_users():
    if not is_admin():
        return redirect(url_for('admin_login'))

    users = User.query.all()
    return render_template('admin_users.html', users=users)

# Add new user
@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        # Retrieve form data safely
        username = request.form.get('username')
        password = request.form.get('password')

        is_admin = 'is_admin' in request.form  # Check if checkbox is selected

        # Handle cases where form fields might be missing
        if not username:
            flash('Username is required!')
            return redirect(url_for('create_user'))

        # Create a new user object
        new_user = User(username=username, password=password, is_admin=is_admin)

        # Add user to database
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('admin_users'))  # Redirect to the user list or another page
    return render_template('create_user.html')


# Edit user page
@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if not is_admin():
        return redirect(url_for('admin_login'))

    user = User.query.get(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        if request.form['password']:  # Update only if a new password is provided
            user.password = request.form['password']
        user.is_admin = 'is_admin' in request.form
        db.session.commit()
        return redirect(url_for('admin_users'))

    return render_template('edit_user.html', user=user)

# Delete user
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_users'))


# Admin logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
