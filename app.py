import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'secret-key'

client = MongoClient('mongodb://localhost:27017/')
db = client['praktikum_db']

# Dummy user untuk login
users = {
    'admin': {'username': 'admin', 'password': 'admin123', 'role': 'admin'},
    'mahasiswa': {'username': 'mahasiswa', 'password': 'mhs123', 'role': 'mahasiswa'},
    'dosen': {'username': 'dosen', 'password': 'dsn123', 'role': 'dosen'}
}

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    for user in users.values():
        if user['username'] == username and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'mahasiswa':
                return redirect(url_for('mahasiswa_dashboard'))
            elif user['role'] == 'dosen':
                return redirect(url_for('dosen_dashboard'))
    return render_template('login.html', error="Username atau password salah")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/mahasiswa')
def mahasiswa_dashboard():
    if session.get('role') != 'mahasiswa':
        return redirect(url_for('home'))
    return render_template('dashboard_mahasiswa.html')

@app.route('/dosen')
def dosen_dashboard():
    if session.get('role') != 'dosen':
        return redirect(url_for('home'))
    return render_template('dashboard_dosen.html')

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    return render_template('dashboard_admin.html')  

@app.route('/admin/data-mahasiswa')
def data_mahasiswa():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    mahasiswa = db.users.find({'role': 'Mahasiswa'})
    return render_template('admin_data_mahasiswa.html', mahasiswa=mahasiswa)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        passwordHash = request.form['passwordHash']
        jurusan = request.form['jurusan']
        role = request.form['role']
        nim = request.form['nim']
        nidn = request.form['nidn']

        # Jika role Mahasiswa, nidn kosongkan
        if role.lower() == 'mahasiswa':
            nidn = ''

        user = {
            'name': name,
            'email': email,
            'passwordHash': passwordHash,
            'jurusan': jurusan,
            'role': role,
            'nim': nim,
            'nidn': nidn,
            'createdAt': datetime.utcnow()
        }

        db.users.insert_one(user)
        return redirect(url_for('index'))

    return render_template('add_user.html')


if __name__ == '__main__':
    app.run(debug=True)
