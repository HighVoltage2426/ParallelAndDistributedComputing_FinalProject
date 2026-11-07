#this contains routes of the webapp

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

views = Blueprint('views', __name__)

# ADMIN CREDENTIALS (one 4-digit PIN per window)
# PIN : which kind of admin, and which window they run
ADMIN_PINS = {
    "1201": {"role": "cashier",   "window": 1},
    "1202": {"role": "cashier",   "window": 2},
    "1203": {"role": "cashier",   "window": 3},
    "1101": {"role": "registrar", "window": 1},
    "1102": {"role": "registrar", "window": 2},
    "1103": {"role": "registrar", "window": 3},
}

@views.route('/')
def home():
    return render_template("base.html")

@views.route('/qCashier')
def qCashier():
    return render_template("qCashier.html")

@views.route('/qRegistrar')
def qRegistrar():
    return render_template("qRegistrar.html")


# ADMIN LOGIN PAGES (Cashier and Registrar)
@views.route('/staff', methods=['GET', 'POST']) 
def login():
    if request.method == 'POST':
        admin = ADMIN_PINS.get(request.form.get('pin'))
        if admin:
            session['role'] = admin['role']
            session['window'] = admin['window']
            if admin['role'] == 'cashier':
                return redirect(url_for('views.cashierControl'))
            return redirect(url_for('views.registrarControl'))
        flash("Incorrect PIN.")
    return render_template("login.html")

@views.route('/cashier')
def cashierControl():
    if session.get('role') != 'cashier':
        return redirect(url_for('views.login'))
    return render_template("cashierControl.html", window=session['window'])

@views.route('/registrar')
def registrarControl():
    if session.get('role') != 'registrar':
        return redirect(url_for('views.login'))
    return render_template("registrarControl.html", window=session['window'])

@views.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('views.login'))