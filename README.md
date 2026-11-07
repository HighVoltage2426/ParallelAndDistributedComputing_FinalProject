# Queue It

High Voltage's final project for Parallel & Distributed Computing. Queue It is a Flask web app prototype with separate pages for the cashier and registrar queues.

## Requirements

- Python 3.9 or newer
- pip (included with most Python installations)

## Setup on Windows

Open PowerShell in the project folder (the folder containing `main.py`), then create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Flask in the active environment:

```powershell
python -m pip install Flask
```

If PowerShell prevents environment activation, use the virtual environment's Python directly for both installation and running:

```powershell
.\.venv\Scripts\python.exe -m pip install Flask
.\.venv\Scripts\python.exe main.py
```

## Run the app

With the virtual environment activated, run:

```powershell
python main.py
```

Open <http://127.0.0.1:5000/> in your browser

## Project layout

```text
.
├── main.py                 # Starts the Flask development server
└── webapp/
    ├── __init__.py          # Creates the Flask app and registers routes
    ├── pages.py             # Page routes
    └── templates/
        ├── base.html        # Home page
        ├── qCashier.html    # Cashier queue page
        └── qRegistrar.html  # Registrar queue page
```

## Development note

The app currently runs in Flask's development mode with debugging enabled. This is suitable for local development only; do not use the development server or debug mode for a public production deployment.

## PINS for Admin (By Windows)

Cashier 1 - 1201
Cashier 2 - 1202
Cashier 3 - 1203
Registrar 1 - 1101
Registrar 2 - 1102
Registrar 3 - 1103
