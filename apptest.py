from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Dummy storage for meetings (in-memory)
meetings = []

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/schedule', methods=['POST'])
def schedule_meeting():
    room = request.form.get('room')
    date = request.form.get('date')
    time = request.form.get('time')
    purpose = request.form.get('purpose')
    
    meeting = {
        'room': room,
        'date': date,
        'time': time,
        'purpose': purpose
    }
    
    meetings.append(meeting)
    print(meetings)
    # Redirect to the home page after scheduling
    return redirect(url_for('login.html'))

if __name__ == '__main__':
    app.run(debug=True)
