import uuid
import sqlite3

from flask import Blueprint, render_template, session, flash, redirect, url_for
from .broker import Broker
from .subscriber import create_queue

client = Blueprint('client', __name__)
dbName = 'HighQ.db'
join_queue = 'JOIN_QUEUE'
broker = Broker()
broker.subscribe(join_queue, create_queue)

#THIS CHECKS IF THE CURRENT DEVICE HAS AN ACTIVE SESSION
def getID():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    return session_id

#HOME
@client.route('/')
def home():
    session_id = getID()
    db = sqlite3.connect(dbName)
    topic = db.execute('SELECT TYPE FROM QUEUE WHERE ID = ?', (session_id,)).fetchone()
    db.close()
    
    if topic is None:
        return render_template("base.html")
    elif topic[0] == "REGISTRAR":
        return redirect(url_for('client.qRegistrar'))
    else:
        return redirect(url_for('client.qCashier'))
    
#CHECKS IF THE CURRENT DEVICE AS AN ACTIVE QUEUE NUMBER
def isExisting(session_id):
    db = sqlite3.connect(dbName)
    cursor = db.execute('SELECT ID FROM QUEUE WHERE ID = ?', (session_id,)).fetchone()
    db.close()
    
    if cursor is None: 
        return False
    else:
        return True
    
#CLIENT GETTING IN LINE    
def line(topic):
    session_id = getID()
    
    if isExisting(session_id):
        db = sqlite3.connect(dbName)
        row = db.execute('SELECT QUEUE, TYPE FROM QUEUE WHERE ID  = ?', (session_id,)).fetchone()
        q_number = row[0]
        q_type = row[1]
        db.close()
        
        if q_type != topic:
            if q_type == 'REGISTRAR':
                return redirect (url_for('client.qRegistrar'))
            else:
                return redirect(url_for('client.qCashier'))  
        return q_number
        
            
    message = {
        'session_id': session_id,
        'topic': topic
    }
    
    broker.publish(join_queue, message)
    flash(f"You have successfully joined the {topic} Queue!")
    db = sqlite3.connect(dbName)
    q_number = db.execute('SELECT QUEUE FROM QUEUE WHERE ID = ?', (session_id,)).fetchone()[0]
    db.close()
    
    return q_number
    
#LINE FOR REGISTRAR
@client.route('/qRegistrar')
def qRegistrar():
    result  = line('REGISTRAR')
    
    if not isinstance(result, int):
        return result
        
    return render_template('qRegistrar.html', q_number = f"{result:03d}")

#LINE FOR CASHIER
@client.route('/qCashier')
def qCashier():
    result  = line('CASHIER')
    
    if not isinstance(result, int):
        return result
        
    return render_template('qCashier.html', q_number = f"{result:03d}")


#EXIT FROM THE LINE
@client.route('/leave')
def leave_queue():
    db = sqlite3.connect(dbName)
    session_id = getID()
    
    print(f'MESSAGE: You have left the queue.')
    
    db.execute('DELETE FROM QUEUE WHERE ID = ?', (session_id,))
    db.commit()
    db.close()
    
    return redirect(url_for('client.home'))