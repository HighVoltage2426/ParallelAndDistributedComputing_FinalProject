#this contains routes of the webapp

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

views = Blueprint('views', __name__)

# PIN FOR LOGIN SCREEN (REGISTRAR)
REGISTRAR_PIN = "1234"

@views.route('/')
def home():
    return render_template("base.html")

@views.route('/qCashier')
def qCashier():
    return render_template("qCashier.html")

@views.route('/qRegistrar')
def qRegistrar():
    return render_template("qRegistrar.html")


# REGISTRAR LOGIN PAGES
@views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('pin') == REGISTRAR_PIN:
            session['is_registrar'] = True
            return redirect(url_for('views.registrarControl'))
        flash("Incorrect PIN.")
    return render_template("login.html")

@views.route('/registrar')
def registrarControl():
    if not session.get('is_registrar'):
        return redirect(url_for('views.login'))
    return render_template("registrarControl.html")

@views.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('views.login'))