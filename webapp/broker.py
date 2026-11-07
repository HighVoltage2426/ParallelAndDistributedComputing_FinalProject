import sqlite3

dbname = "HighQ.db"

class Broker:

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, topic, callback):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
            
        self.subscribers[topic].append(callback)

    def publish(self, topic, message):
        
        open_db = sqlite3.connect(dbname)
        open_db.execute('''INSERT INTO QUEUE (ID, QUEUE, TYPE) VALUES (?,?,?)''',
                        (message["session_id"], message["queue_number"], message["topic"]))
        
        open_db.commit()
        open_db.close()
        
        if topic in self.subscribers:
            
            for callback in self.subscribers[topic]:
                callback(message)