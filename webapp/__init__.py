from flask import Flask

def createApp():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'High Voltage' #Secures the session and cookie data
    
    from .pages import pages
    app.register_blueprint(pages, url_prefix = '/')
    
    return app  