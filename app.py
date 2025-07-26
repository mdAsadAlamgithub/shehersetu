from flask import Flask, request, render_template, redirect, url_for,session,flash, render_template_string, jsonify
import sqlite3, os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

DB_NAME = 'database.db'

# Create table on first run
def init_db():
    with sqlite3.connect('database.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                username TEXT,
                email TEXT,
                age INTEGER,
                society_name TEXT,
                block TEXT,
                floor TEXT,
                flat TEXT,
                mobile_number TEXT
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue TEXT,
                location TEXT,
                status TEXT DEFAULT 'Pending',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                image_of_issue TEXT
            );
        ''')

init_db()

@app.route('/logine', methods=['GET', 'POST'])
def logine():
    if request.method == 'POST':
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT mobile_number FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]== mobile_number:
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or mobile_number.', 'error')
    return render_template('logine.html')

# @app.route('/login')
# def login():
#     return render_template("login.html")

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('logine'))
    return render_template('dashboard.html', email=session['email'])
    

@app.route('/geolocation',methods=['GET', 'POST'])
def geolocation():
    if 'email' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('logine'))
    return render_template('geolocation.html', email=session['email'])
    

@app.route('/logout')
def logout():
    session.pop('email', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('logine'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        try:
            with sqlite3.connect('database.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (
                        role, username, email, age,
                        society_name, block, floor, flat, mobile_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['role'],
                    data['username'],
                    data['email'],
                    data['age'],
                    data['society_name'],
                    data['block'],
                    data['floor'],
                    data['flat'],
                    data['mobile_number']
                ))
                conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('logine'))
        except sqlite3.OperationalError as e:
            return f"❌ Database error: {e}"
    return render_template("login.html")

@app.route('/users')
def users():
    if 'email' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('logine'))
    with sqlite3.connect('database.db') as conn:
        cursor = conn.execute('SELECT * FROM users')
        users = cursor.fetchall()

    return render_template_string('''
        <h2>All Users</h2>
        <ul>
            {% for user in users %}
                <li>{{ user[0] }} - {{ user[2] }} - {{ user[3] }} - {{ user[4] }}</li>
            {% endfor %}
        </ul>
    ''', email=session['email'])

@app.route('/recent_complaints')
def recent_complaints():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.execute('''
            SELECT issue, location, status
            FROM complaints
            ORDER BY timestamp DESC
            LIMIT 5
        ''')
        complaints = cursor.fetchall()
    return render_template_string('''                    
        {% for issue, location, status in complaints %}                       
        <div class="complaint-row">
            <span>{{ issue }}</span>
            <span>{{ location }}</span>
            <span class="badge {{ status|lower|replace(' ', '_') }}">{{ status }}</span>
        </div>
        {% endfor %}
    ''', complaints=complaints)

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'email' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('logine'))
    issue = request.form.get("issue")
    location = request.form.get("location")
    image = request.files.get("image")
    status = "Pending"

    image_path = None
    if image:
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)

    try:
        with sqlite3.connect("database.db") as conn:
            conn.execute('''
                INSERT INTO complaints (issue, location, status, image_of_issue)
                VALUES (?, ?, ?, ?)
            ''', (issue, location, status, image_path))
            conn.commit()
        return redirect(url_for('view_complaints'))
    except sqlite3.Error as e:
        return jsonify({"message": f"Database error: {e}"}), 500

@app.route('/view_complaints')
def view_complaints():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.execute('SELECT id, issue, location, status, timestamp, image_of_issue FROM complaints')
        complaints = cursor.fetchall()

    return render_template_string('''
        <h2>📜 All Complaints</h2>
        <ul>
        {% for c in complaints %}
          <li>
            <strong>{{ c[1] }}</strong> ({{ c[2] }}) - <em>{{ c[3] }}</em> at {{ c[4] }}
            {% if c[5] %}<br><img src="/{{ c[5] }}" width="100">{% endif %}
          </li>
        {% endfor %}
        </ul>
    ''', complaints=complaints)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT or default to 5000
    app.run(host='0.0.0.0', port=port)
