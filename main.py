from webapp import createApp
import sqlite3
import os

app = createApp()

dbName = 'HighQ.db'

if not os.path.exists(dbName):
    
    db = sqlite3.connect(dbName)
    
    db.executescript(''' CREATE TABLE IF NOT EXISTS QUEUE (
                        ID TEXT PRIMARY KEY NOT NULL,
                        QUEUE INT NOT NULL,
                        TYPE TEXT NOT NULL);
                        
                        CREATE TABLE IF NOT EXISTS SERVING (
                        ID TEXT PRIMARY KEY NOT NULL,
                        QUEUE INT NOT NULL,
                        WINDOW INT NOT NULL,
                        TYPE TEXT NOT NULL);
                        
                        CREATE TABLE IF NOT EXISTS COMPLETED (
                        ID TEXT PRIMARY KEY NOT NULL,
                        QUEUE INT NOT NULL,
                        WINDOW INT NOT NULL,
                        TYPE TEXT NOT NULL);
                     ''')    
    db.close()

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
    
