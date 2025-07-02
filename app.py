from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'secret-key'

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
    return render_template('dashboard_admin.html')  # Pastikan ini punya link ke /admin/data-mahasiswa

@app.route('/admin/data-mahasiswa')
def data_mahasiswa():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    mahasiswa = [
        {"nim": "2023001", "nama": "Ahmad Naufal", "email": "naufal@mail.com", "jurusan": "Informatika"},
        {"nim": "2023002", "nama": "Siti Aminah", "email": "aminah@mail.com", "jurusan": "Sistem Informasi"},
        {"nim": "2023003", "nama": "Rizki Pratama", "email": "rizki@mail.com", "jurusan": "Teknik Komputer"},
    ]
    return render_template('admin_data_mahasiswa.html', mahasiswa=mahasiswa)

@app.route('/admin/data-dosen')
def data_dosen():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    dosen = [
        {"nip": "19850101", "nama": "Dr. Yusuf", "email": "yusuf@mail.com", "jurusan": "Informatika"},
        {"nip": "19850202", "nama": "Sari Dewi", "email": "sari@mail.com", "jurusan": "Sistem Informasi"},
        {"nip": "19850303", "nama": "Bambang Irawan", "email": "bambang@mail.com", "jurusan": "Teknik Komputer"}
    ]
    return render_template('admin_data_dosen.html', dosen=dosen)

@app.route('/admin/tambah-dosen', methods=['POST'])
def tambah_dosen():
    # Untuk saat ini hanya redirect ulang, simpan data di database jika ingin dinamis
    return redirect(url_for('data_dosen'))

if __name__ == '__main__':
    app.run(debug=True)
