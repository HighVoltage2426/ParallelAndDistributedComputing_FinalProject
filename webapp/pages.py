from flask import Blueprint, render_template,session
import uuid
import sqlite3

pages = Blueprint('pages', __name__)
dbName = "HighQ.db"

@pages.route('/')
def home():
    return render_template("base.html")

@pages.route('/qCashier')
def qCashier():
    return render_template("qCashier.html")

#QUEUE FOR REGISTRAR

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
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    
    if isExisting(session_id,):
        cursor = open_db.execute('SELECT QUEUE FROM QUEUE WHERE ID = ?', (session_id,))
        personal_queue_number = cursor.fetchone()[0]
        return render_template ('qRegistrar.html', queue_number=personal_queue_number)

    cursor = open_db.execute ('SELECT MAX(QUEUE) FROM QUEUE')
    result = cursor.fetchone()
                            
    if result[0] is None:
        queue_number = 1
    else:
        queue_number = result[0] + 1
        
    open_db.execute('INSERT INTO QUEUE (ID, QUEUE, TYPE) VALUES (?,?,?)', (session_id, queue_number, "REGISTRAR"))
    open_db.commit()
        
    open_db.close()
    
    return render_template ('qRegistrar.html', queue_number=queue_number)
