import sqlite3
import threading
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

auth = Blueprint('auth', __name__)
dbName = "HighQ.db"

queue_lock = threading.Lock()   # Avoids two windows possibly serving the same queue number

# ADMIN CREDENTIALS (one 4-digit PIN per window)
# 2 Roles: Customer and Registrar
ADMIN_PINS = {
    "1101": {"role": "cashier",   "window": 1},
    "1102": {"role": "cashier",   "window": 2},
    "1103": {"role": "cashier",   "window": 3},
    "1201": {"role": "registrar", "window": 1},
    "1202": {"role": "registrar", "window": 2},
    "1203": {"role": "registrar", "window": 3},
}

# DATABASE METHODS
def line_status(line, window): # Shows the number that a specific window is serving 
    """Returns (number this window is serving or None, how many are still waiting)."""
    db = sqlite3.connect(dbName)
    row = db.execute('SELECT QUEUE FROM SERVING WHERE TYPE = ? AND WINDOW = ?',
                     (line, window)).fetchone()
    waiting = db.execute('''SELECT COUNT(*) FROM QUEUE
                            WHERE TYPE = ?
                              AND QUEUE NOT IN (SELECT QUEUE FROM SERVING
                                                WHERE TYPE = ? AND QUEUE IS NOT NULL)''',
                         (line, line)).fetchone()[0]
    db.close()
    return (row[0] if row else None), waiting


def control_page(): 
    return url_for('auth.cashierControl' if session.get('role') == 'cashier'
                   else 'auth.registrarControl')

def waiting_list(q_type):
    db = sqlite3.connect(dbName)
    list = db.execute("SELECT QUEUE FROM QUEUE WHERE TYPE = ?", (q_type,)).fetchall()
    
    return list
    
# LOGIN METHODS
@auth.route('/login', methods=['POST'])
def login_screen():
    return render_template('login.html')

# CASHIER AND REGISTRAR ADMIN LOGIN PAGES
@auth.route('/admin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin = ADMIN_PINS.get(request.form.get('pin'))
        if admin:
            session['role'] = admin['role']
            session['window'] = admin['window']
            if admin['role'] == 'cashier':
                return redirect(url_for('auth.cashierControl'))
            return redirect(url_for('auth.registrarControl'))
        flash("Incorrect PIN.")
    return render_template("login.html")


@auth.route('/cashier')
def cashierControl():
    type = "CASHIER"
    
    if session.get('role') != 'cashier':
        return redirect(url_for('auth.login'))
    
    serving, waiting = line_status('CASHIER', session['window'])
    
    list = waiting_list(type)
    
    return render_template("cashierControl.html", window=session ['window'], current_client=serving, total_waiting=waiting, waiting_list = list)

@auth.route('/registrar')
def registrarControl():
    if session.get('role') != 'registrar':
        return redirect(url_for('auth.login'))
    serving, waiting = line_status('REGISTRAR', session['window'])
    return render_template("registrarControl.html", window=session['window'],
                           serving=serving, waiting=waiting)

@auth.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# NEXT BUTTON LOGIC METHODS
@auth.route('/next', methods=['POST'])
def next_customer():
    if session.get('role') not in ('cashier', 'registrar'):
        return redirect(url_for('auth.login'))

    line = session['role'].upper()  # role = cashier or registrar
    window = session['window'] # window number

    with queue_lock:
        db = sqlite3.connect(dbName)

        # 1. Delete current customer data 
        current = db.execute('SELECT QUEUE FROM SERVING WHERE TYPE = ? AND WINDOW = ?',
                             (line, window)).fetchone()
        if current and current[0] is not None:
            db.execute('DELETE FROM QUEUE WHERE TYPE = ? AND QUEUE = ?', (line, current[0]))

        # 2. Move to the next number (Determine the lowest queue number)
        nxt = db.execute('''SELECT QUEUE FROM QUEUE
                            WHERE TYPE = ?
                              AND QUEUE NOT IN (SELECT QUEUE FROM SERVING
                                                WHERE TYPE = ? AND QUEUE IS NOT NULL)
                            ORDER BY QUEUE LIMIT 1''', (line, line)).fetchone()
        number = nxt[0] if nxt else None

        # 3. Remember what customer number this window is currently serving
        db.execute('INSERT OR REPLACE INTO SERVING (TYPE, WINDOW, QUEUE) VALUES (?, ?, ?)',
                   (line, window, number))
        db.commit()
        db.close()

    # if there is nobody in the line (most likely first customer)
    if number is None: 
        flash("Nobody is waiting in this line.")
    return redirect(control_page())


# FINISH BUTTON LOGIC METHODS
@auth.route('/finish', methods=['POST'])
def finish():
    if session.get('role') not in ('cashier', 'registrar'):
        return redirect(url_for('auth.login'))

    with queue_lock:
        db = sqlite3.connect(dbName)
        db.execute('DELETE FROM QUEUE')      # delete all data from the database
        db.execute('DELETE FROM SERVING')
        db.commit()
        db.close()

    flash("All queue data was cleared.")
    return redirect(control_page())