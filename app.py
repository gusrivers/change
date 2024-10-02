from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
from functools import wraps
import os
from flask_talisman import Talisman
from flask_mail import Mail, Message
#import smtplib


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/sala'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
mail = Mail(app)
db = SQLAlchemy(app)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')
print(app.secret_key)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.strptime)

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

@app.route('/static/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js'), 200, {'Content-Type': 'application/javascript'}


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

def send_invitation_email(email, user, room, start_time, end_time, purpose):
    print(f"Sending email for room: {room.name} by {user.username}")  # Debugging
    subject = f"Convite de reunião para {purpose} às {start_time.strftime('%H:%M')}"
    body = (f"Você foi convidado(a) por {user.username} para a reunião com motivo de: {purpose} "
            f"na sala {room.name} às {start_time.strftime('%H:%M')}.\n\n"
            f"Sala: {room.name}\nHorário: {start_time.strftime('%H:%M')}\n")
    
    send_email(email, subject, body)


def send_email(to, subject, body):
    msg = Message(subject=subject,
                  recipients=[to],
                  body=body,
                  sender=app.config['MAIL_USERNAME'])
    with app.app_context():
        mail.send(msg)

from datetime import datetime, time, timedelta

@app.route('/room/<int:room_id>/schedule', methods=['GET' ,'POST'])
def room_schedule(room_id):
    room = Room.query.get_or_404(room_id)

    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')
        purpose = data.get('purpose')
        invitees = data.get('invitees')
        if invitees:
            invitees = [email.strip() for email in invitees.split(',')]
        else:
            invitees = []


        # Get start time from form data
        start_time_str = data.get('start_time')
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
            except ValueError:
                return jsonify({"error": "Invalid start time format"}), 400
        else:
            return jsonify({"error": "Start time is required"}), 400

        end_time = (datetime.combine(datetime.today(), start_time) + timedelta(hours=1)).time()

        # Fetch the user details (including email) from the database
        user = User.query.filter_by(username=username).first()

        if not user or user.password != password:
            return jsonify({"error": "Usuário ou senha incorretos!"}), 401

        if start_time < time(8, 0) or end_time > time(18, 0):
            return jsonify({"error": "Meetings can only be scheduled between 8 AM and 6 PM"}), 400

        # Check for conflicts
        conflicts = Meeting.query.filter_by(room_id=room_id).filter(
            Meeting.start_time < end_time,  # Meeting starts before the new meeting ends
            Meeting.end_time > start_time   # Meeting ends after the new meeting starts
        ).all()

        if conflicts:
            for conflict in conflicts:
                print(f"Conflict with meeting ID {conflict.id}: {conflict.start_time} to {conflict.end_time}")
            return jsonify({"error": "The room is already booked for the requested time"}), 409

        # Create a new meeting
        new_meeting = Meeting(
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            booked_by=user.username
        )

        db.session.add(new_meeting)
        db.session.commit()

        # Prepare email details for the invitees
        subject = f"Meeting Invitation: {purpose} at {start_time.strftime('%H:%M')}"
        body = f"You have been invited to a meeting for the purpose of '{purpose}' in room '{room.name}' at {start_time.strftime('%H:%M')}.\n\nDetails:\nRoom: {room.name}\nStart Time: {start_time.strftime('%H:%M')}\nEnd Time: {end_time.strftime('%H:%M')}."

        send_email(user.email, subject, f"Sua reunião foi agendada com sucesso!! \n\nSala: {room.name}\nMotivo: {purpose}\nHorário: {start_time}")

        invitee_emails = []
        for invitee_email in invitees:
            invitee_user = User.query.filter_by(email=invitee_email).first()
            if invitee_user:
                invitee_emails.append(invitee_user.email)
            else:
                print(f"Invitee '{invitee_email}' not found in the database")  # Log missing invitees

        for email in invitee_emails:
            send_invitation_email(email, user, room, start_time, end_time, purpose)

        return jsonify({"message": "Meeting scheduled successfully, invitations sent", "meeting_id": new_meeting.id}), 201

    users = User.query.all()
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

    return render_template('room.html', room=room, schedule=schedule, users=users)

def is_admin():
    return session.get('is_admin', False)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.password == password and user.is_admin:
            session['admin_logged_in'] = True
            session['is_admin'] = user.is_admin
            return redirect(url_for('admin_users'))
        
        flash('Usuário e senha incorretos ou usuário não permitido!')
        return redirect(url_for('admin_login'))
        
    return render_template('admin_login.html')

@app.route('/admin/users')
def admin_users():
    if not is_admin():
        return redirect(url_for('admin_login'))

    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        is_admin = 'is_admin' in request.form

        if not username:
            flash('Username is required!')
            return redirect(url_for('create_user'))

        new_user = User(username=username, password=password, email=email, is_admin=is_admin)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('admin_users'))
    return render_template('create_user.html')


@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if not is_admin():
        return redirect(url_for('admin_login'))

    user = User.query.get(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        if request.form['password']:
            user.password = request.form['password']
        user.is_admin = 'is_admin' in request.form
        db.session.commit()
        return redirect(url_for('admin_users'))

    return render_template('edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_users'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(ssl_context=('server.cert', 'server.key'), debug=True, host='0.0.0.0')


