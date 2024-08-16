from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@127.0.0.1/meeting_scheduler'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the meeting model
class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(200), nullable=False)

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/schedule', methods=['POST'])
def schedule_meeting():
    data = request.get_json()
    room = data.get('room')
    date = data.get('date')
    time = data.get('time')
    purpose = data.get('purpose')
    
    new_meeting = Meeting(room=room, date=date, time=time, purpose=purpose)
    db.session.add(new_meeting)
    db.session.commit()
    print(new_meeting)
    return jsonify({'status': 'success', 'message': 'Meeting scheduled successfully'})

if __name__ == '__main__':
#    db.create_all()  # Create tables
    app.run(debug=True)
