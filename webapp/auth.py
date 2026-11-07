from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth = Blueprint('auth', __name__)

# ADMIN CREDENTIALS (one 4-digit PIN per window)
# PIN : which kind of admin, and which window they run
ADMIN_PINS = {
    "1101": {"role": "cashier",   "window": 1},
    "1102": {"role": "cashier",   "window": 2},
    "1103": {"role": "cashier",   "window": 3},
    "1201": {"role": "registrar", "window": 1},
    "1202": {"role": "registrar", "window": 2},
    "1203": {"role": "registrar", "window": 3},
}

@auth.route('/login', methods=['POST'])
def login_screen():
    return render_template('login.html')

# ADMIN LOGIN PAGES (Cashier and Registrar)
@auth.route('/staff', methods=['GET', 'POST']) 
def login():
    if request.method == 'POST':
        admin = ADMIN_PINS.get(request.form.get('pin'))
        if admin:
            session['role'] = admin['role']
            session['window'] = admin['window']
            if admin['role'] == 'cashier':
                return redirect(url_for('auth.cashierControl'))
            return redirect(url_for('auth.registrarControl'))
        flash("Incorrect PIN.")
    return render_template("login.html")

@auth.route('/cashier')
def cashierControl():
    if session.get('role') != 'cashier':
        return redirect(url_for('auth.login'))
    return render_template("cashierControl.html", window=session['window'])

@auth.route('/registrar')
def registrarControl():
    if session.get('role') != 'registrar':
        return redirect(url_for('auth.login'))
    return render_template("registrarControl.html", window=session['window'])

@auth.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))