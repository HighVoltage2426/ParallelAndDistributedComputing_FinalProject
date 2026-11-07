#this contains routes of the webapp

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

views = Blueprint('views', __name__)

# ADMIN CREDENTIALS (one 4-digit PIN per window)
# PIN : which kind of admin, and which window they run
ADMIN_PINS = {
    "1101": {"role": "cashier",   "window": 1},
    "1102": {"role": "cashier",   "window": 2},
    "1103": {"role": "cashier",   "window": 3},
    "1201": {"role": "registrar", "window": 1},
    "1202": {"role": "registrar", "window": 2},
    "1203": {"role": "registrar", "window": 3},
}

@views.route('/')
from flask import Blueprint, render_template,session
import uuid
import sqlite3
from .broker import Broker
from .subscriber import subscriber

pages = Blueprint('pages', __name__)
dbName = "HighQ.db"

@pages.route('/')
def home():
    return render_template("base.html")

@pages.route('/qCashier')
def qCashier():
    return render_template("qCashier.html")


#QUEUE FOR REGISTRAR
broker = Broker()

def isExisting(session_id):
    open_db = sqlite3.connect(dbName)
    cursor = open_db.execute('SELECT ID FROM QUEUE WHERE ID = ?', (session_id,))
    existing = cursor.fetchone()
    
    if existing is None:
        return False
    else: 
        return True
    
@pages.route('/qRegistrar', methods = ['POST'])
def qRegistrar():
    open_db = sqlite3.connect(dbName)
    topic = "REGISTRAR"
    
    broker = Broker()
    broker.subscribe(topic, subscriber)
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    
    if isExisting(session_id,):
        personal_queue_number = open_db.execute('SELECT QUEUE FROM QUEUE WHERE ID = ?', (session_id,)).fetchone()[0]
        open_db.close()
        return render_template ('qRegistrar.html', queue_number=personal_queue_number)
    
    max = open_db.execute("SELECT MAX(QUEUE) FROM QUEUE").fetchone
                            
    if max[0] is None:
        queue_number = 1
    else:
        queue_number = max[0] + 1
    
    broker.publish("REGISTRAR", {"session_id": session_id, "queue_number": queue_number, "topic": topic})    
    
    open_db.close()
    
    return render_template ('qRegistrar.html', queue_number=queue_number)


# ADMIN LOGIN PAGES (Cashier and Registrar)
@views.route('/staff', methods=['GET', 'POST']) 
def login():
    if request.method == 'POST':
        admin = ADMIN_PINS.get(request.form.get('pin'))
        if admin:
            session['role'] = admin['role']
            session['window'] = admin['window']
            if admin['role'] == 'cashier':
                return redirect(url_for('views.cashierControl'))
            return redirect(url_for('views.registrarControl'))
        flash("Incorrect PIN.")
    return render_template("login.html")

@views.route('/cashier')
def cashierControl():
    if session.get('role') != 'cashier':
        return redirect(url_for('views.login'))
    return render_template("cashierControl.html", window=session['window'])

@views.route('/registrar')
def registrarControl():
    if session.get('role') != 'registrar':
        return redirect(url_for('views.login'))
    return render_template("registrarControl.html", window=session['window'])

@views.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('views.login'))