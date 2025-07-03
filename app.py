from datetime import datetime
import os
import gridfs
from bson.objectid import ObjectId
from flask import Flask, flash, render_template, request, redirect, send_from_directory, url_for, session
from pymongo import MongoClient
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'secret-key'

client = MongoClient('mongodb://localhost:27017/')
db = client['studyRoom']
fs = gridfs.GridFS(db)


# Folder penyimpanan file
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)




@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    print("===== DEBUG POST DATA =====")
    print(request.form)
    print("============================")

    email = request.form.get('email')
    password = request.form.get('password')

    user = db.users.find_one({'email': email, 'passwordHash': password})
    print(user)
    if user:
        session['email'] = email
        session['role'] = user['role']
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user['role'] == 'Mahasiswa':
            return redirect(url_for('mahasiswa_dashboard'))
        elif user['role'] == 'Dosen':
            return redirect(url_for('dosen_dashboard'))

    return render_template('login.html', error="Email atau password salah")



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/mahasiswa')
def mahasiswa_dashboard():
    if session.get('role') != 'Mahasiswa':
        return redirect(url_for('home'))
    jadwal = db.schedule.find()
    return render_template('dashboard_mahasiswa.html',jadwal_list=jadwal)

@app.route('/mahasiswa/progress')
def mahasiswa_progress():
    if session.get('role') != 'Mahasiswa':
        return redirect(url_for('home'))

    laporan_list = list(db.tugas_collection.find())
    
    # Gunakan salah satu tugas untuk parameter `tugas_id` sementara
    tugas = laporan_list[0] if laporan_list else None

    return render_template('dashboard_mahasiswa_progress.html',
                           laporan_list=laporan_list,
                           tugas=tugas)

@app.route('/dosen')
def dosen_dashboard():
    if session.get('role') != 'Dosen':
        return redirect(url_for('home'))
    return render_template('dashboard_dosen.html')

@app.route('/upload_tugas', methods=['GET', 'POST'])
def upload_tugas():
    if request.method == 'POST':    
        judul = request.form['judul']
        deadline = request.form['deadline']
        mata_kuliah_id = request.form['mata_kuliah_id']
        pertemuan = request.form['pertemuan']
        catatan = request.form['catatan']
        file = request.files['file']

        file_id = fs.put(file, filename=file.filename, content_type=file.content_type)

        db.tugas_collection.insert_one({
            'judul': judul,
            'deadline': deadline,
            'mata_kuliah_id': ObjectId(mata_kuliah_id),
            'pertemuan': pertemuan,
            'catatan': catatan,
            'file_id': file_id,
            'filename': file.filename
        })

        return redirect(url_for('upload_tugas'))

    # Ambil daftar tugas
    matakuliah_list = db.mata_kuliah.find()    
    return render_template('dashboard_dosen_laporan.html',mata_kuliah_list=matakuliah_list)
@app.route('/daftar_tugas', methods=['GET', 'POST'])
def daftar_tugas():
    laporan=db.laporan_mahasiswa.find()
    
    return render_template('dashboard_dosen_daftar_tugas.html',laporan=laporan)

# Route untuk akses file
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/mahasiswa/laporan')
def lihat_laporan():
    if session.get('role') != 'Mahasiswa':
        return redirect(url_for('home'))


    
    laporan = db.tugas_collection.find()

    return render_template('dashboard_mahasiswa_daftarTugas.html', laporan_list=laporan)

@app.route('/mahasiswa/kehadiran')
def mahasiswa_kehadiran():
    if session.get('role') != 'Mahasiswa':
        return redirect(url_for('home'))

    username = session['email']
    kehadiran = list(db.kehadiran.find({'email': username}))
    daftar_matkul = list(db.mata_kuliah.find())

    # Hitung ringkasan
    total_hadir = sum(1 for k in kehadiran if k['status'] == 'Hadir')
    total_izin = sum(1 for k in kehadiran if k['status'] == 'Izin')
    total_alpha = sum(1 for k in kehadiran if k['status'] == 'Alpha')

    return render_template(
        'dashboard_mahasiswa_kehadiran.html',
        kehadiran=kehadiran,
        tanggal_hari_ini=datetime.now().strftime('%Y-%m-%d'),
        daftar_matkul=daftar_matkul,
        total_hadir=total_hadir,
        total_izin=total_izin,
        total_alpha=total_alpha
    )
@app.route('/mahasiswa/upload-tugas', methods=['GET', 'POST'])
def upload_tugas_mahasiswa():
    if session.get('role') != 'Mahasiswa':
        return redirect(url_for('home'))

    if request.method == 'POST':
        nama = request.form['nama']
        pertemuan = request.form['laporan']
        file = request.files['file']

        # Simpan file ke GridFS
        file_id = fs.put(file, filename=file.filename, content_type=file.content_type)

        # Simpan metadata
        db.laporan_mahasiswa.insert_one({
            'nama': nama,
            'pertemuan': pertemuan,
            'file_id': file_id,
            'filename': file.filename,
            'status': 'Menunggu',
            'catatan': '',
            'uploaded_at': datetime.utcnow()
        })

        flash('Laporan berhasil diupload.')
        return redirect(url_for('mahasiswa_progress'))

    return render_template('dashboard_mahasiswa_upload_tugas.html')


@app.route('/mahasiswa/absen', methods=['POST'])
def absen_mahasiswa():
    if session.get('role') != 'Mahasiswa':
        return redirect(url_for('home'))

    data = {
        'email': session['email'],
        'tanggal': request.form['tanggal'],
        'matkul': request.form['matkul'],
        'pertemuan': request.form['pertemuan'],
        'status': request.form['keterangan'],
        'verifikasi':'belum verifikasi',
        'waktu_absen': datetime.utcnow()
    }

    # Cegah absensi ganda
    existing = db.kehadiran.find_one({
        'email': data['email'],
        'tanggal': data['tanggal'],
        'matkul': data['matkul'],
        'verifikasi':'belum verifikasi',
        'pertemuan': data['pertemuan']
    })

    if not existing:
        db.kehadiran.insert_one(data)

    return redirect(url_for('mahasiswa_kehadiran'))


@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    daftar_dosen = db.users.find({'role': 'Dosen'})
    jadwal_list = db.schedule.find()
    mata_kuliah_cursor = db.mata_kuliah.find()
    edit_jadwal = None
    edit_id = request.args.get('edit_id')
    if edit_id:
        edit_jadwal = db.schedule.find_one({'_id': ObjectId(edit_id)})
    
    mata_kuliah = []
    for mk in mata_kuliah_cursor:
        mk['_id'] = str(mk['_id'])  # Ubah ObjectId jadi string
        mata_kuliah.append(mk)

    return render_template('dashboard_admin.html',
                           daftar_dosen=daftar_dosen,
                           mata_kuliah=mata_kuliah,
                           jadwal_list=jadwal_list,
                            edit_jadwal=edit_jadwal)

@app.route('/admin/tambah-jadwal', methods=['POST'])
def tambah_jadwal():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    mata_praktikum_id = request.form.get('mata_praktikum')
    pertemuan = request.form.get('pertemuan')
    hari = request.form.get('hari')
    jam = request.form.get('jam')
    ruangan = request.form.get('ruangan')
    dosen = request.form.get('dosen')

    # Optional: Ambil nama mata kuliah dari ID-nya jika kamu ingin menyimpan nama juga
    matkul = db.mata_kuliah.find_one({'_id': ObjectId(mata_praktikum_id)})
    nama_matkul = matkul['nama'] if matkul else 'Unknown'

    schedule = {
        'mata_praktikum_id': ObjectId(mata_praktikum_id),
        'mata_praktikum': nama_matkul,
        'pertemuan': pertemuan,
        'hari': hari,
        'jam': jam,
        'ruangan': ruangan,
        'dosen': dosen
    }

    db.schedule.insert_one(schedule)
    flash('Jadwal berhasil ditambahkan.')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/edit-jadwal/<id>', methods=['POST'])
def edit_jadwal(id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    mata_praktikum_id = request.form.get('mata_praktikum')
    pertemuan = request.form.get('pertemuan')
    hari = request.form.get('hari')
    jam = request.form.get('jam')
    ruangan = request.form.get('ruangan')
    dosen = request.form.get('dosen')

    # Ambil nama matkul dari ID
    matkul = db.mata_kuliah.find_one({'_id': ObjectId(mata_praktikum_id)})
    nama_matkul = matkul['nama'] if matkul else 'Unknown'

    updated_data = {
        'mata_praktikum_id': ObjectId(mata_praktikum_id),
        'mata_praktikum': nama_matkul,
        'pertemuan': pertemuan,
        'hari': hari,
        'jam': jam,
        'ruangan': ruangan,
        'dosen': dosen
    }

    db.schedule.update_one({'_id': ObjectId(id)}, {'$set': updated_data})
    flash('Jadwal berhasil diedit.')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/hapus-jadwal/<id>', methods=['POST'])
def hapus_jadwal(id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    db.schedule.delete_one({'_id': ObjectId(id)})
    flash('Jadwal berhasil dihapus.')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/data-mahasiswa')
def data_mahasiswa():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    mahasiswa = db.users.find({'role': 'Mahasiswa'})
    return render_template('admin_data_mahasiswa.html', mahasiswa=mahasiswa)


@app.route('/admin/data-dosen')
def data_dosen():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    dosen = db.users.find({'role': 'Dosen'})
    return render_template('admin_data_dosen.html', dosen=dosen)

@app.route('/admin/tambah-dosen', methods=['POST'])
def tambah_dosen():
    # Untuk saat ini hanya redirect ulang, simpan data di database jika ingin dinamis
    return redirect(url_for('data_dosen'))

@app.route('/admin/mata-kuliah')
def data_mata_kuliah():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    mata_kuliah = db.mata_kuliah.find()
    return render_template('admin_data_matkul.html', mata_kuliah=mata_kuliah)
    
@app.route('/admin/tambah-mata-kuliah', methods=['POST'])
def tambah_mata_kuliah():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    kode = request.form['kode']
    nama = request.form['nama']
    jurusan = request.form['jurusan']
    pertemuan = request.form['totalPertemuan']
    try:
        total_pertemuan = int(pertemuan)
    except ValueError:
        return render_template(
            'admin_data_matkul.html',
            error="Total pertemuan harus berupa angka."
        )
    mk = {
        'kode': kode,
        'nama': nama,
        'jurusan': jurusan,
        'totalPertemuan': total_pertemuan,
    }
    db.mata_kuliah.insert_one(mk)
    return redirect(url_for('data_mata_kuliah'))
@app.route('/admin/hapus-mata-kuliah/<id>', methods=['POST'])
def hapus_mata_kuliah(id):
    if session.get('role') != 'admin':
        return redirect(url_for('home'))

    db.mata_kuliah.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('data_mata_kuliah'))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        jurusan = request.form['jurusan']
        nim = request.form['nim']

        # Jika role Mahasiswa, nidn kosongkan
        

        user = {
            'name': name,
            'email': email,
            'passwordHash': nim,
            'jurusan': jurusan,
            'role': 'Mahasiswa',
            'nim': nim,
            'nidn': '',
            'createdAt': datetime.utcnow()
        }

        db.users.insert_one(user)
        return redirect(url_for('data_mahasiswa'))

    return render_template('add_user.html')

@app.route('/add_user_dosen', methods=['GET', 'POST'])
def add_user_dosen():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        jurusan = request.form['jurusan']
        nipn = request.form['nipn']

        # Jika role Mahasiswa, nidn kosongkan
        

        user = {
            'name': name,
            'email': email,
            'passwordHash': nipn,
            'jurusan': jurusan,
            'role': 'Dosen',
            'nim': '',
            'nidn': nipn,
            'createdAt': datetime.utcnow()
        }

        db.users.insert_one(user)
        return redirect(url_for('data_dosen'))

    return render_template('admin_data_dosen.html')
@app.route('/dosen/kehadiran', methods=['GET', 'POST'])
def list_kehadiran():
    if session.get('role') != 'Dosen':
        return redirect(url_for('home'))

    # Ambil daftar mata kuliah untuk dropdown
    daftar_matkul = list(db.mata_kuliah.find())

    selected_matkul = request.args.get('matkul')
    filter_query = {}
    if selected_matkul:
        filter_query['matkul'] = selected_matkul

    kehadiran = list(db.kehadiran.find(filter_query))

    return render_template(
        'dashboard_dosen_verifikasi.html',
        daftar_matkul=daftar_matkul,
        selected_matkul=selected_matkul,
        kehadiran=kehadiran
    )


@app.route('/dosen/verifikasi_kehadiran/<kehadiran_id>', methods=['POST'])
def verifikasi_kehadiran(kehadiran_id):
    if session.get('role') != 'Dosen':
        return redirect(url_for('home'))

    db.kehadiran.update_one(
        {'_id': ObjectId(kehadiran_id)},
        {'$set': {'verifikasi': 'Terverifikasi'}}
    )
    flash('Kehadiran berhasil diverifikasi.')
    return redirect(request.referrer or url_for('list_kehadiran'))


if __name__ == '__main__':
    app.run(debug=True)

