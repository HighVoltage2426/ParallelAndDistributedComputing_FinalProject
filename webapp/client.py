from flask import Blueprint, render_template,session
import uuid
import sqlite3
from .broker import Broker
from .subscriber import subscriber

client = Blueprint('client', __name__)
dbName = "HighQ.db"

@client.route('/')
def home():
    return render_template("base.html")

@client.route('/qCashier')
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
    
@client.route('/qRegistrar', methods = ['POST'])
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
    
    max = open_db.execute("SELECT MAX(QUEUE) FROM QUEUE").fetchone()[0]
                            
    if max is None:
        queue_number = 1
    else:
        queue_number = max + 1
    
    broker.publish("REGISTRAR", {"session_id": session_id, "queue_number": queue_number, "topic": topic})    
    
    open_db.close()
    
    return render_template ('qRegistrar.html', queue_number=queue_number)


