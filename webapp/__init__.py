from flask import Flask

def createApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'High Voltage' #Secures the session and cookie data
    
    from .client import client
    from .auth import auth
    
    app.register_blueprint(client, url_prefix = '/')
    app.register_blueprint(auth, url_prefix = '/')
    
    return app  