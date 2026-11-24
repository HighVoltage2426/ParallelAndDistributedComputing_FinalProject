from datetime import datetime, timedelta, timezone
import re
import threading
import time
from zoneinfo import ZoneInfo
import httpx
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from supabase_client import supabase
from .broker import broker
UTC = timezone.utc

auth = Blueprint('auth', __name__)
QUEUE_TABLE = 'QUEUEU'
SERVING_TABLE = 'SERVING'
COMPLETED_TABLE = 'COMPLETED'

queue_lock = threading.Lock()

MANILA_TZ = ZoneInfo("Asia/Manila")


def now_manila():
    return datetime.now(MANILA_TZ)


# ADMIN CREDENTIALS (one 4-digit PIN per window)
ADMIN_PINS = {
    "1101": {"role": "cashier",   "window": 1},
    "1102": {"role": "cashier",   "window": 2},
    "1103": {"role": "cashier",   "window": 3},
    "1201": {"role": "registrar", "window": 1},
    "1202": {"role": "registrar", "window": 2},
    "1203": {"role": "registrar", "window": 3},
}

window_statuses = {
    "CASHIER": {1: "close", 2: "close", 3: "close"},
    "REGISTRAR": {1: "close", 2: "close", 3: "close"},
}


def execute_with_retry(query_builder, retries=2, delay=0.15):
    for attempt in range(retries + 1):
        try:
            return query_builder.execute()
        except (httpx.RemoteProtocolError, httpx.TransportError):
            if attempt == retries:
                raise
            time.sleep(delay)


def _normalize_iso(ts):
    """Pad/trim fractional seconds to 6 digits so Python 3.10 can parse it."""
    s = str(ts).replace("Z", "+00:00")
    m = re.match(r"^(.*?\.)(\d+)(.*)$", s)
    if m:
        s = m.group(1) + m.group(2)[:6].ljust(6, "0") + m.group(3)
    return s


def _parse_iso_ts(ts):
    if not ts:
        return None
    dt = datetime.fromisoformat(_normalize_iso(ts))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt

#average service time per topic
DEFAULT_SERVICE_SECONDS = 180.0
def avg_service_seconds(topic):
    rows = execute_with_retry(
        supabase.table(COMPLETED_TABLE)
        .select('started_at, completed_at')
        .eq('topic', topic)
    )

    durations = []
    for row in rows.data or []:
        start = _parse_iso_ts(row.get('started_at'))
        end = _parse_iso_ts(row.get('completed_at'))
        if start and end:
            diff = (end - start).total_seconds()
            if diff >= 0:
                durations.append(diff)

    if not durations:
        return DEFAULT_SERVICE_SECONDS

    return sum(durations) / len(durations)


# publish queue status for a topic to all subscribers
def publish_queue_status(topic):
    serving_res = execute_with_retry(
        supabase.table(SERVING_TABLE)
        .select('window, q_number')
        .eq('topic', topic)
    )
    serving_by_window = {row['window']: row['q_number'] for row in serving_res.data}

    windows_info = {}
    for win in (1, 2, 3):
        windows_info[win] = {
            "status": window_statuses[topic].get(win, "close"),
            "serving": serving_by_window.get(win),
        }

    avg_sec = avg_service_seconds(topic)

    message = {
        "topic": topic,
        "windows": windows_info,
        "avg_service_seconds": avg_sec,
    }
    broker.publish(topic, message)
    return message


# status of the line (how many people are in line and who is currently being served)
def line_status(line, window):
    row_res = execute_with_retry(
        supabase.table(SERVING_TABLE)
        .select('q_number')
        .eq('topic', line)
        .eq('window', window)
        .limit(1)
    )
    serving_num = row_res.data[0]['q_number'] if row_res.data else None

    serving_all_res = execute_with_retry(
        supabase.table(SERVING_TABLE)
        .select('q_number')
        .eq('topic', line)
        .not_.is_('q_number', 'null')
    )
    serving_nums = {r['q_number'] for r in serving_all_res.data}

    queue_res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('q_number')
        .eq('topic', line)
    )
    waiting = sum(1 for r in queue_res.data if r['q_number'] not in serving_nums)

    return serving_num, waiting


def control_page():
    return url_for(
        'auth.cashierControl' if session.get('role') == 'cashier' else 'auth.registrarControl'
    )


def format_joined_time(ts):
    if not ts:
        return "-"
    try:
        dt = _parse_iso_ts(ts)
        return dt.astimezone(MANILA_TZ).strftime("%I:%M:%S %p") if dt else "-"
    except ValueError:
        return str(ts)

# clients in line
def waiting_list(q_type):
    res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('q_number, created_at')
        .eq('topic', q_type)
        .order('q_number')
    )
    return [
        {
            "q_number": r['q_number'],
            "joined_at": format_joined_time(r.get('created_at')),
        }
        for r in res.data
    ]

#calculate the total clients served within the day
def completed_total(q_type):
    now = datetime.now(MANILA_TZ)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    res = execute_with_retry(
        supabase.table(COMPLETED_TABLE)
        .select('id', count='exact')
        .eq('topic', q_type)
        .gte('completed_at', start_of_day.isoformat())
        .lt('completed_at', end_of_day.isoformat())
    )
    return res.count or 0


#average service time per window
def avg_service(topic, window):
    rows = execute_with_retry(
        supabase.table(COMPLETED_TABLE)
        .select('started_at, completed_at')
        .eq('topic', topic)
        .eq('window', window)
    )

    durations = []
    for row in rows.data or []:
        start = _parse_iso_ts(row.get('started_at'))
        end = _parse_iso_ts(row.get('completed_at'))
        if start and end:
            diff = (end - start).total_seconds()
            if diff >= 0:
                durations.append(diff)

    if not durations:
        return "0.0 sec."

    average_service_time = sum(durations) / len(durations)
    if average_service_time < 60:
        return f"{average_service_time:.0f} sec."
    elif average_service_time >= 60 and average_service_time < (60*60):
        return f"{round(average_service_time / 60):.0f} min."
    else:
        return f"{round(average_service_time / (60*60)):.0f} hr."


# LOGIN METHODS
@auth.route('/login', methods=['POST'])
def login_screen():
    return render_template('login.html')


# CASHIER AND REGISTRAR ADMIN LOGIN PAGES
@auth.route('/admin', methods=['GET', 'POST'])
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


# WINDOW STATUS (PUBLISHER EVENT)
@auth.route('/change_window_status', methods=['POST'])
def change_window_status():
    if session.get('role') not in ('cashier', 'registrar'):
        return redirect(url_for('auth.login'))

    topic = session['role'].upper()
    window = session['window']
    new_status = request.form.get('window_status', 'close')

    if new_status in ('open', 'break', 'close'):
        session['window_status'] = new_status
        window_statuses[topic][window] = new_status

        if new_status in ('break', 'close'):
            with queue_lock:
                currently_serving = execute_with_retry(
                    supabase.table(SERVING_TABLE)
                    .select("*")
                    .eq("topic", topic)
                    .eq("window", window)
                    .limit(1)
                )

                if currently_serving.data and currently_serving.data[0].get("q_number") is not None:
                    execute_with_retry(
                        supabase.table(COMPLETED_TABLE).insert({
                            "started_at": currently_serving.data[0].get("created_at"),
                            "q_number": currently_serving.data[0]["q_number"],
                            "topic": currently_serving.data[0]["topic"],
                            "window": currently_serving.data[0]["window"],
                        })
                    )

                execute_with_retry(
                    supabase.table(SERVING_TABLE)
                    .delete()
                    .eq("topic", topic)
                    .eq("window", window)
                )

        publish_queue_status(topic)

    return redirect(control_page())


@auth.route('/cashier')
def cashierControl():
    topic = "CASHIER"

    if session.get('role') != 'cashier':
        return redirect(url_for('auth.login'))

    window = session['window']
    window_status = window_statuses[topic].get(window, 'close')
    serving, waiting = line_status('CASHIER', window)
    queue_rows = waiting_list(topic)
    total_completed = completed_total(topic)
    current_date = now_manila().strftime("%A, %B %d, %Y")
    service_time = avg_service(topic, window)

    return render_template(
        "cashierControl.html",
        window=window,
        window_status=window_status,
        current_date=current_date,
        current_client=serving,
        total_waiting=waiting,
        average_service=service_time,
        total_completed=total_completed,
        waiting_list=queue_rows,
    )


@auth.route('/cashier_status')
def cashier_status():
    if session.get('role') != 'cashier':
        return jsonify({"error": "Unauthorized"}), 401

    topic = "CASHIER"
    window = session['window']
    serving, waiting = line_status(topic, window)
    queue_tickets = waiting_list(topic)
    total_completed = completed_total(topic)
    service = avg_service(topic, window)

    return jsonify({
        "current_client": serving,
        "total_waiting": waiting,
        "total_completed": total_completed,
        "average_service": service,
        "waiting_list": queue_tickets,
    })


@auth.route('/registrar')
def registrarControl():
    topic = "REGISTRAR"

    if session.get('role') != 'registrar':
        return redirect(url_for('auth.login'))

    window = session['window']
    window_status = window_statuses[topic].get(window, 'close')
    serving, waiting = line_status('REGISTRAR', window)
    queue_rows = waiting_list(topic)
    total_completed = completed_total(topic)
    current_date = now_manila().strftime("%A, %B %d, %Y")
    service = avg_service(topic, window)

    return render_template(
        "registrarControl.html",
        window=window,
        window_status=window_status,
        current_date=current_date,
        current_client=serving,
        total_waiting=waiting,
        total_completed=total_completed,
        average_service=service,
        waiting_list=queue_rows,
    )


@auth.route('/registrar_status')
def registrar_status():
    if session.get('role') != 'registrar':
        return jsonify({"error": "Unauthorized"}), 401

    topic = "REGISTRAR"
    window = session['window']
    serving, waiting = line_status(topic, window)
    queue_tickets = waiting_list(topic)
    total_completed = completed_total(topic)
    service = avg_service(topic, window)

    return jsonify({
        "current_client": serving,
        "total_waiting": waiting,
        "total_completed": total_completed,
        "average_service": service,
        "waiting_list": queue_tickets,
    })


@auth.route('/logout', methods=['POST'])
def logout():
    role = session.get('role')
    window = session.get('window')

    if role in ('cashier', 'registrar') and window is not None:
        topic = role.upper()
        with queue_lock:
            currently_serving = execute_with_retry(
                supabase.table(SERVING_TABLE)
                .select("*")
                .eq("topic", topic)
                .eq("window", window)
                .limit(1)
            )

            if currently_serving.data and currently_serving.data[0].get("q_number") is not None:
                execute_with_retry(
                    supabase.table(COMPLETED_TABLE).insert({
                        "started_at": currently_serving.data[0].get("created_at"),
                        "q_number": currently_serving.data[0]["q_number"],
                        "topic": topic,
                        "window": window,
                    })
                )

            execute_with_retry(
                supabase.table(SERVING_TABLE)
                .delete()
                .eq("topic", topic)
                .eq("window", window)
            )

            window_statuses[topic][window] = 'close'
            publish_queue_status(topic)

    session.clear()
    session.pop('q_number', None)
    return redirect(url_for('auth.login'))


# NEXT BUTTON 
@auth.route('/next', methods=["POST"])
def next_customer():
    if session.get('role') not in ('cashier', 'registrar'):
        return redirect(url_for('auth.login'))

    window = session['window']
    topic = session['role'].upper()

    if window_statuses[topic].get(window, 'close') != 'open':
        flash("Window is currently on break or closed.")
        return redirect(control_page())

    with queue_lock:
        next_in_line = execute_with_retry(
            supabase.table(QUEUE_TABLE)
            .select("*")
            .eq("topic", topic)
            .order("q_number", desc=False)
            .limit(1)
        )

        currently_serving = execute_with_retry(
            supabase.table(SERVING_TABLE)
            .select("*")
            .eq("topic", topic)
            .eq("window", window)
            .limit(1)
        )

        if next_in_line.data:
            if currently_serving.data:
                execute_with_retry(
                    supabase.table(COMPLETED_TABLE).insert({
                        "started_at": currently_serving.data[0]["created_at"],
                        "q_number": currently_serving.data[0]["q_number"],
                        "topic": currently_serving.data[0]["topic"],
                        "window": currently_serving.data[0]["window"],
                    })
                )

                execute_with_retry(
                    supabase.table(SERVING_TABLE).update({
                        "q_number": next_in_line.data[0]["q_number"],
                    }).eq("topic", topic).eq("window", window)
                )
            else:
                execute_with_retry(
                    supabase.table(SERVING_TABLE).insert({
                        "q_number": next_in_line.data[0]["q_number"],
                        "topic": topic,
                        "window": window,
                    })
                )

            execute_with_retry(
                supabase.table(QUEUE_TABLE).delete().eq("id", next_in_line.data[0]["id"])
            )

        elif currently_serving.data:
            execute_with_retry(
                supabase.table(COMPLETED_TABLE).insert({
                    "started_at": currently_serving.data[0]["created_at"],
                    "q_number": currently_serving.data[0]["q_number"],
                    "topic": currently_serving.data[0]["topic"],
                    "window": currently_serving.data[0]["window"],
                })
            )

            execute_with_retry(
                supabase.table(SERVING_TABLE).delete().eq("id", currently_serving.data[0]["id"])
            )

        publish_queue_status(topic)

    return redirect(control_page())