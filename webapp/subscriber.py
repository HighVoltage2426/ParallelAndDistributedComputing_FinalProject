import sqlite3

dbName = "HighQ.db"

def create_queue(message):
    
    session_id = message['session_id']
    topic = message['topic']
    
    db = sqlite3.connect(dbName)
    
    existing = db.execute('SELECT ID FROM QUEUE WHERE ID = ?', (session_id,)).fetchone()
    if existing:
        db.close()
        return
    
    recent = db.execute('SELECT MAX(QUEUE) FROM QUEUE WHERE TYPE = ?', (topic,)).fetchone()
    if recent[0] is None:
        q_number = 1
    else:
        q_number = recent[0] + 1
    
    db.execute('INSERT INTO QUEUE (ID, QUEUE, TYPE) VALUES (?, ?, ?)', (session_id, q_number, topic))
    db.commit()
    db.close()
    
    print(f"MESSAGE: Created {topic} queue number {q_number}")
        