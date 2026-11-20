from flask import Flask

def createApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'High Voltage'
    
    from .pages import pages
    app.register_blueprint(pages, url_prefix = '/')
    
    from .client import client
    app.register_blueprint(client, url_prefix = '/')
    
    return app  