from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt, os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/sala'
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Available')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(255))
    booked_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    room = db.relationship('Room', backref=db.backref('meetings', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful.')
            return redirect(url_for('rooms'))
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('login'))


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


@app.route('/room/<int:room_id>', methods=['GET', 'POST'])
def room_schedule(room_id):
    room = Room.query.get_or_404(room_id)
    meetings = Meeting.query.filter_by(room_id=room.id).all()

    if request.method == 'POST':
        start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
        purpose = request.form.get('purpose')
        booked_by = request.form.get('booked_by')

        if start_time < time(8, 0) or end_time > time(18, 0):
            return jsonify({"error": "Meetings can only be scheduled between 8 AM and 6 PM"}), 400

        conflicts = Meeting.query.filter_by(room_id=room_id).filter(
            Meeting.start_time < end_time,
            Meeting.end_time > start_time
        ).all()

        if conflicts:
            return jsonify({"error": "The room is already booked for the requested time"}), 409

        new_meeting = Meeting(
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            booked_by=booked_by
        )

        db.session.add(new_meeting)
        db.session.commit()

        return jsonify({"message": "Meeting scheduled successfully", "meeting_id": new_meeting.id}), 201

    schedule = []
    start_hour = 9
    end_hour = 18

    for hour in range(start_hour, end_hour):
        time_slot = {
            "time": f"{hour}:00",
            "status": "Available",
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

@app.route('/room/<int:room_id>/schedule', methods=['POST'])
def book_meeting(room_id):
    room = Room.query.get_or_404(room_id)
    data = request.form

    start_time = datetime.strptime(data['start_time'], '%H:%M').time()
    end_time = datetime.strptime(data['end_time'], '%H:%M').time()
    purpose = data.get('purpose')
    booked_by = data.get('booked_by')

    # Ensure the meeting is within working hours
    if start_time < time(9, 0) or end_time > time(18, 0):
        return jsonify({"error": "Meetings can only be scheduled between 9 AM and 6 PM"}), 400

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
        booked_by=booked_by
    )

    db.session.add(new_meeting)
    db.session.commit()

    return jsonify({"message": "Meeting scheduled successfully", "meeting_id": new_meeting.id}), 201





if __name__ == '__main__':
    #with app.app_context():
    #    db.create_all()
    app.run(debug=True)
