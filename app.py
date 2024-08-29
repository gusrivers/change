from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/sala'
db = SQLAlchemy(app)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    capacity = db.Column(db.Integer)
    status = db.Column(db.String(20), default='Available')

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    purpose = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Occupied')


@app.route('/')
def rooms():
    rooms = Room.query.all()
    return render_template('main.html', rooms=rooms)

@app.route('/room/<int:room_id>')
def room_schedule(room_id):
    room = Room.query.get_or_404(room_id)
    schedules = Schedule.query.filter_by(room_id=room_id).all()
    return render_template('room.html', room=room, schedules=schedules)


@app.route('/api/room/<int:room_id>/schedule', methods=['GET', 'POST'])
def manage_schedule(room_id):
    if request.method == 'GET':
        schedules = Schedule.query.filter_by(room_id=room_id).all()
        schedule_data = [{
            'time': f"{schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')}",
            'status': schedule.status,
            'purpose': schedule.purpose
        } for schedule in schedules]
        return jsonify(schedule_data)

    if request.method == 'POST':
        data = request.json
        start_time = datetime.strptime(data['time'], '%H:%M')
        end_time = start_time + timedelta(hours=1)
        purpose = data['purpose']

        new_schedule = Schedule(room_id=room_id, start_time=start_time, end_time=end_time, purpose=purpose, status='Occupied')
        db.session.add(new_schedule)
        db.session.commit()
        return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)
