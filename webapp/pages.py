#this contains routes of the webapp

from flask import Blueprint, render_template

views = Blueprint('views', __name__)

@views.route('/')
def home():
    return render_template("base.html")

@views.route('/qCashier')
def qCashier():
    return render_template("qCashier.html")

@views.route('/qRegistrar')
def qRegistrar():
    return render_template("qRegistrar.html")