from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
from werkzeug.utils import secure_filename
import os
import datetime
from flask_login import login_required, current_user, LoginManager, login_user, logout_user


app = Flask(__name__)
app.secret_key = 'your secret key'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User:
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

# Load user
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('mydatabase.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    if user:
        return User(user[0], user[1], user[2], user[3])
    return None

UPLOAD_FOLDER = 'files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST','GET'])
def login():
    msg=""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('mydatabase.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email=? AND password=?',(email,password,))
        user = c.fetchone()
        if user == None:
            msg="Username/password wrong"
            return render_template('login.html', msg=msg)
        else:
            if user:
                user_obj = User(user[0], user[1], user[2], user[3])
                login_user(user_obj)
                return redirect(url_for('upload_file'))
    else:
        return render_template('login.html')
        

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST','GET'])
@login_required
def upload_file():
    if request.method == 'GET':
        return render_template('upload.html')
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        username= current_user.username
        conn = sqlite3.connect('mydatabase.db')
        c = conn.cursor()
        c.execute("INSERT INTO files (name, type, size, created_at, download_count, uploader) VALUES (?, ?, ?, ?,?,?)",
                  (filename, file.content_type, file.content_length, datetime.datetime.now(),0, username,))
        conn.commit()
        conn.close()
        file_url = url_for('uploaded_file', filename=filename)
        return redirect(url_for('sucess', value=file_url, filename=filename, username= username))
    else:
        return render_template('upload.html', msg="Invalid file type")


@app.route('/sucess')
def sucess():
    conn = sqlite3.connect('mydatabase.db')
    filename = request.args.get('filename')
    username = request.args.get('username')
    c = conn.cursor()
    c.execute("SELECT download_Count, type FROM files WHERE name=?",(filename,))
    count= c.fetchone()
    value = request.args.get('value')
    return render_template('sucess.html', url=value, count=count[0], filename= filename, type =count[1], uploader= username)

@app.route('/profile/<username>')
def show_profile(username):
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, email FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    cursor.execute('SELECT name, download_count FROM files WHERE uploader = ?', (username,))
    files = cursor.fetchall()
    return render_template('profile.html', user=user, files=files)

@app.route('/register', methods=['POST','GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn =sqlite3.connect('mydatabase.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        user = c.fetchone()
        if user:
            error = 'A user with that username or email address already exists.'
            return render_template('register.html', error=error)
        c.execute("INSERT INTO users (username, email, password, name) VALUES (?,?,?,?)", (username,email,password,name,))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/files/<filename>')
def uploaded_file(filename):
    conn = sqlite3.connect('mydatabase.db')
    c = conn.cursor()
    c.execute("UPDATE files SET download_count= download_count + 1  WHERE name=? ",(filename,))
    conn.commit()
    conn.close()
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/reset', methods=["GET","POST"])
@login_required
def reset():
    if request.method == 'POST':
        new_pass = request.form['new_pass']
        email = request.form['email']
        username = current_user.username
        conn = sqlite3.connect('mydatabase.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND email = ?', (username, email))
        user = c.fetchone()

        if user is None:
            return render_template('reset.html', msg="please input correct email")

        c.execute("UPDATE users SET password=? WHERE username=? AND email=?", (new_pass,username,email))
        conn.commit()
        c.close()
        conn.close()
        msg="sucess"
        return render_template('reset.html', msg=msg)
    else:
        return render_template('reset.html')

@app.route('/all_files/<int:page>')
def all_files(page):
    if current_user.is_authenticated:
        per_page = 8 
        offset = (page - 1) * per_page
        conn = sqlite3.connect('mydatabase.db')
        c = conn.cursor()
        c.execute('SELECT * FROM files ORDER BY created_at DESC LIMIT ? OFFSET ?', (per_page, offset,))
        files = c.fetchall()
        c.execute('SELECT COUNT(*) FROM files')
        total = c.fetchone()[0]
        pages = total // per_page + 1
        return render_template('home.html', files=files, page=page, pages=pages)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

'''@app.route('/rupload', methods=['POST','GET'])
def upload():
    if request.method == 'POST':
        url = request.form['url']
        response = requests.get(url)
        if response.status_code == 200:
            file = response.content
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            username= current_user.username
            conn = sqlite3.connect('mydatabase.db')
            c = conn.cursor()
            c.execute("INSERT INTO files (name, type, size, created_at, download_count, uploader) VALUES (?, ?, ?, ?,?,?)",(filename, file.content_type, file.content_length, datetime.datetime.now(),0, username,))
            conn.commit()
            conn.close()
            # Generate a URL for the uploaded file
            file_url = url_for('uploaded_file', filename=filename)
            return redirect(url_for('sucess', value=file_url, filename=filename, username= username))
        else:
            return render_template('rupload.html', msg="invalid URL or file not found.")
    else:
        return render_template('rupload.html')
   '''

if __name__ == '__main__':
    app.run(debug=True)