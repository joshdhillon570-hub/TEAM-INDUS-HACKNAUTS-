from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import sqlite3
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'database.db'
app = Flask(__name__)
app.secret_key = 'smartcare-demo-secret'

DEPARTMENTS = ['General Medicine', 'Cardiology', 'Orthopedics', 'Pediatrics', 'Dermatology']
DOCTORS = {
    'General Medicine': ['Dr. Sharma', 'Dr. Mehta'],
    'Cardiology': ['Dr. Kapoor'],
    'Orthopedics': ['Dr. Singh'],
    'Pediatrics': ['Dr. Kaur'],
    'Dermatology': ['Dr. Bedi']
}
SYMPTOMS = ['Fever', 'Cough', 'Headache', 'Chest pain', 'Breathing difficulty', 'Injury/pain', 'Skin problem', 'Stomach pain', 'None / routine visit']


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        patient_name TEXT NOT NULL,
        age INTEGER NOT NULL,
        phone TEXT NOT NULL,
        department TEXT NOT NULL,
        doctor TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        symptoms TEXT NOT NULL,
        previous_info TEXT,
        triage TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Waiting',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        note_type TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id)
    );
    CREATE TABLE IF NOT EXISTS demo_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    ''')
    count = conn.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
    if count == 0:
        demo = [
            ('A24', 'Aman', 29, '9876500001', 'General Medicine', 'Dr. Sharma', '2026-10-03', '09:30 AM', 'Follow-up visit', 'Previous visit: routine check-up', 'LOW', 'Completed'),
            ('A25', 'Simran', 24, '9876500002', 'General Medicine', 'Dr. Sharma', '2026-10-03', '10:00 AM', 'Headache', 'No known previous information', 'MEDIUM', 'With Doctor'),
            ('A26', 'Arjun', 31, '9876500003', 'General Medicine', 'Dr. Sharma', '2026-10-03', '10:15 AM', 'Fever, Cough', 'No known previous information', 'MEDIUM', 'Waiting'),
            ('A27', 'Rahul', 20, '9876500004', 'General Medicine', 'Dr. Sharma', '2026-10-03', '10:30 AM', 'Breathing difficulty', 'No previous medical information', 'HIGH', 'Waiting')
        ]
        for row in demo:
            conn.execute('''INSERT INTO appointments
                (token, patient_name, age, phone, department, doctor, appointment_date, appointment_time, symptoms, previous_info, triage, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (*row, datetime.now().isoformat(timespec='seconds')))
        conn.execute("INSERT OR REPLACE INTO demo_meta(key,value) VALUES('seeded','1')")
    conn.commit()
    conn.close()


def triage_for(symptoms):
    s = (symptoms or '').lower()
    if any(x in s for x in ['chest pain', 'breathing difficulty']):
        return 'HIGH'
    if any(x in s for x in ['fever', 'cough', 'headache', 'injury', 'stomach pain']):
        return 'MEDIUM'
    return 'LOW'


def queue_position(appt):
    conn = get_db()
    rows = conn.execute('''SELECT id FROM appointments
        WHERE appointment_date=? AND doctor=? AND status IN ('Waiting','With Doctor')
        ORDER BY CASE triage WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, id''',
        (appt['appointment_date'], appt['doctor'])).fetchall()
    ids = [r['id'] for r in rows]
    conn.close()
    if appt['status'] == 'Completed':
        return 0
    return ids.index(appt['id']) + 1 if appt['id'] in ids else len(ids)


def serialize(appt):
    if not appt:
        return None
    pos = queue_position(appt)
    wait = max(0, (pos - 1) * 6)
    return {**dict(appt), 'queue_position': pos, 'estimated_wait': wait}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/appointment')
def appointment():
    return render_template('appointment.html', departments=DEPARTMENTS, doctors=DOCTORS, symptoms=SYMPTOMS, today=date.today().isoformat())


@app.route('/book', methods=['POST'])
def book():
    data = request.form
    department = data.get('department', '')
    doctor = data.get('doctor', '')
    if department not in DEPARTMENTS or doctor not in DOCTORS.get(department, []):
        flash('Please select a valid department and doctor.')
        return redirect(url_for('appointment'))
    symptoms = data.get('symptoms', '').strip() or 'None / routine visit'
    triage = triage_for(symptoms)
    conn = get_db()
    last = conn.execute("SELECT token FROM appointments WHERE token LIKE 'A%' ORDER BY id DESC LIMIT 1").fetchone()
    number = int(last['token'][1:]) + 1 if last else 1
    token = f'A{number}'
    cur = conn.execute('''INSERT INTO appointments
        (token, patient_name, age, phone, department, doctor, appointment_date, appointment_time, symptoms, previous_info, triage, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Waiting', ?)''',
        (token, data['patient_name'].strip(), int(data['age']), data['phone'].strip(), department, doctor,
         data['appointment_date'], data['appointment_time'], symptoms, data.get('previous_info', '').strip(), triage,
         datetime.now().isoformat(timespec='seconds')))
    appt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return redirect(url_for('confirmation', appointment_id=appt_id))


@app.route('/confirmation/<int:appointment_id>')
def confirmation(appointment_id):
    conn = get_db()
    appt = conn.execute('SELECT * FROM appointments WHERE id=?', (appointment_id,)).fetchone()
    conn.close()
    if not appt:
        return redirect(url_for('appointment'))
    return render_template('confirmation.html', appt=serialize(appt))


@app.route('/track/<int:appointment_id>')
def track(appointment_id):
    conn = get_db()
    appt = conn.execute('SELECT * FROM appointments WHERE id=?', (appointment_id,)).fetchone()
    conn.close()
    if not appt:
        return jsonify({'error': 'Appointment not found'}), 404
    return jsonify(serialize(appt))


@app.route('/api/departments')
def departments():
    return jsonify(DOCTORS)


@app.route('/doctor-login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        if request.form.get('doctor_id') == 'doctor' and request.form.get('password') == 'smartcare':
            session['doctor'] = 'Dr. Sharma'
            return redirect(url_for('doctor_dashboard'))
        flash('Demo credentials: doctor / smartcare')
    return render_template('doctor_login.html')


@app.route('/doctor/logout')
def doctor_logout():
    session.pop('doctor', None)
    return redirect(url_for('index'))


def require_doctor():
    return 'doctor' in session


@app.route('/doctor')
def doctor_dashboard():
    if not require_doctor():
        return redirect(url_for('doctor_login'))
    return render_template('doctor_dashboard.html', doctor=session['doctor'])


@app.route('/api/queue')
def api_queue():
    if not require_doctor():
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM appointments WHERE appointment_date=? ORDER BY id", (date.today().isoformat(),)).fetchall()
    conn.close()
    items = [serialize(r) for r in rows]
    return jsonify({'appointments': items, 'stats': {
        'waiting': sum(1 for x in items if x['status'] == 'Waiting'),
        'current': next((x['patient_name'] for x in items if x['status'] == 'With Doctor'), '—'),
        'high': sum(1 for x in items if x['triage'] == 'HIGH' and x['status'] != 'Completed'),
        'today': len(items)
    }})


@app.route('/doctor/patient/<int:appointment_id>')
def patient_details(appointment_id):
    if not require_doctor():
        return redirect(url_for('doctor_login'))
    conn = get_db()
    appt = conn.execute('SELECT * FROM appointments WHERE id=?', (appointment_id,)).fetchone()
    notes = conn.execute('SELECT * FROM notes WHERE appointment_id=? ORDER BY id DESC', (appointment_id,)).fetchall()
    conn.close()
    if not appt:
        return redirect(url_for('doctor_dashboard'))
    return render_template('patient_details.html', appt=serialize(appt), notes=notes)


@app.route('/doctor/patient/<int:appointment_id>/status', methods=['POST'])
def update_status(appointment_id):
    if not require_doctor():
        return jsonify({'error': 'Unauthorized'}), 401
    status = request.form.get('status')
    if status not in ['Waiting', 'With Doctor', 'Completed']:
        return jsonify({'error': 'Invalid status'}), 400
    conn = get_db()
    conn.execute('UPDATE appointments SET status=? WHERE id=?', (status, appointment_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('doctor_dashboard'))


@app.route('/doctor/patient/<int:appointment_id>/note', methods=['POST'])
def add_note(appointment_id):
    if not require_doctor():
        return redirect(url_for('doctor_login'))
    content = request.form.get('content', '').strip()
    note_type = request.form.get('note_type', 'Doctor Note')
    if content:
        conn = get_db()
        conn.execute('INSERT INTO notes(appointment_id,note_type,content,created_at) VALUES(?,?,?,?)',
                     (appointment_id, note_type, content, datetime.now().isoformat(timespec='seconds')))
        conn.commit()
        conn.close()
    return redirect(url_for('patient_details', appointment_id=appointment_id))


@app.route('/api/patient/<int:appointment_id>')
def api_patient(appointment_id):
    conn = get_db()
    appt = conn.execute('SELECT * FROM appointments WHERE id=?', (appointment_id,)).fetchone()
    conn.close()
    if not appt:
        return jsonify({'error': 'Appointment not found'}), 404
    return jsonify(serialize(appt))


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
