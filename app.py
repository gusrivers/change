from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/sala'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Available')
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
            return jsonify({"error": "Invalid username or password"}), 401

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

if __name__ == '__main__':
    app.run(debug=True)
