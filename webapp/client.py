from datetime import datetime
import time
import uuid
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, session, flash, redirect, url_for, jsonify
import httpx
from supabase_client import supabase
from .broker import broker

from .auth import window_statuses

client = Blueprint('client', __name__)
QUEUE_TABLE = 'QUEUEU'
SERVING_TABLE = 'SERVING'

MANILA_TZ = ZoneInfo("Asia/Manila")


def now_manila():
    return datetime.now(MANILA_TZ)


def execute_with_retry(query_builder, retries=2, delay=0.15):
    for attempt in range(retries + 1):
        try:
            return query_builder.execute()
        except (httpx.RemoteProtocolError, httpx.TransportError):
            if attempt == retries:
                raise
            time.sleep(delay)


# Stores the latest published message received by each subscriber (session_id)
subscriber_inbox = {}


# SUBSCRIBER CALLBACK FACTORY
def create_subscriber_callback(session_id):
    def receive_update(message):
        subscriber_inbox[session_id] = message
    return receive_update


# HELPER: Subscribe student to chosen topic and ensure initial window status exists
def subscribe_student(session_id, topic):
    callback = create_subscriber_callback(session_id)
    broker.subscribe(topic, callback, subscriber_id=session_id)

    if session_id not in subscriber_inbox:
        serving_res = execute_with_retry(
            supabase.table(SERVING_TABLE)
            .select('window, q_number')
            .eq('topic', topic)
        )
        serving_by_window = {row['window']: row['q_number'] for row in serving_res.data}

        subscriber_inbox[session_id] = {
            "topic": topic,
            "windows": {
                win: {
                    "status": window_statuses[topic].get(win, "close"),
                    "serving": serving_by_window.get(win),
                }
                for win in (1, 2, 3)
            },
        }

    return subscriber_inbox[session_id]["windows"]


# THIS CHECKS IF THE CURRENT DEVICE HAS AN ACTIVE SESSION
def getID():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    return session_id


# HOME
@client.route('/')
def home():
    session_id = getID()
    res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('topic')
        .eq('id', session_id)
        .limit(1)
    )

    registrar_waiting = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('id', count='exact')
        .eq('topic', 'REGISTRAR')
    )

    cashier_waiting = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('id', count='exact')
        .eq('topic', 'CASHIER')
    )

    registrar_wait_count = registrar_waiting.count or 0
    cashier_wait_count = cashier_waiting.count or 0
    current_date = now_manila().strftime("%A, %B %d, %Y")

    if not res.data:
        return render_template(
            "base.html",
            current_date=current_date,
            registrar_wait_count=registrar_wait_count,
            cashier_wait_count=cashier_wait_count,
        )

    topic = res.data[0]['topic']
    if topic == "REGISTRAR":
        return redirect(url_for('client.qRegistrar'))
    else:
        return redirect(url_for('client.qCashier'))


# CHECKS IF THE CURRENT DEVICE HAS AN ACTIVE QUEUE NUMBER
def isExisting(session_id):
    res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('id')
        .eq('id', session_id)
        .limit(1)
    )

    if not res.data:
        return False
    else:
        return True


# CLIENT GETTING IN LINE (SUBSCRIBER)
def line(topic):
    session_id = getID()

    if isExisting(session_id):
        row_res = execute_with_retry(
            supabase.table(QUEUE_TABLE)
            .select('q_number, topic')
            .eq('id', session_id)
            .limit(1)
        )
        row = row_res.data[0]
        q_number = row['q_number']
        q_type = row['topic']
        session['q_number'] = q_number
        session['topic'] = q_type

        if q_type != topic:
            if q_type == 'REGISTRAR':
                return redirect(url_for('client.qRegistrar'))
            else:
                return redirect(url_for('client.qCashier'))

        ahead_res = execute_with_retry(
            supabase.table(QUEUE_TABLE)
            .select('id', count='exact')
            .eq('topic', q_type)
            .lt('q_number', q_number)
        )
        number_infront = ahead_res.count or 0
        wait_time = number_infront * 3
        windows = subscribe_student(session_id, q_type)

        return q_number, number_infront, wait_time, windows

    latest_res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('q_number')
        .eq('topic', topic)
        .order('q_number', desc=True)
        .limit(1)
    )

    if not latest_res.data:
        q_number = 1
    else:
        q_number = latest_res.data[0]['q_number'] + 1

    session['q_number'] = q_number
    session['topic'] = topic

    # Generate a fresh UUID per new queue entry so repeat visits never collide
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id

    execute_with_retry(
        supabase.table(QUEUE_TABLE).insert({
            'id': session_id,
            'q_number': q_number,
            'topic': topic,
        })
    )

    flash(f"You have successfully joined the {topic} Queue!")

    current_res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('q_number')
        .eq('id', session_id)
        .limit(1)
    )
    q_number = current_res.data[0]['q_number']
    session['q_number'] = q_number

    ahead_res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('id', count='exact')
        .eq('topic', topic)
        .lt('q_number', q_number)
    )
    number_infront = ahead_res.count or 0
    wait_time = number_infront * 3

    # Subscribe student to the chosen topic (REGISTRAR or CASHIER)
    windows = subscribe_student(session_id, topic)

    return q_number, number_infront, wait_time, windows


# LINE FOR REGISTRAR
@client.route('/qRegistrar')
def qRegistrar():
    result = line('REGISTRAR')

    if not isinstance(result, tuple):
        return result

    return render_template(
        'qRegistrar.html',
        header_title="Registrar Queue",
        q_number=f"{result[0]:03d}",
        number_infront=result[1],
        wait_time=result[2],
        windows=result[3],
    )


# LINE FOR CASHIER
@client.route('/qCashier')
def qCashier():
    result = line('CASHIER')

    if not isinstance(result, tuple):
        return result

    return render_template(
        'qCashier.html',
        header_title="Cashier Queue",
        q_number=f"{result[0]:03d}",
        number_infront=result[1],
        wait_time=result[2],
        windows=result[3],
    )


# LIVE STATUS ENDPOINT FOR SUBSCRIBER POLLING
@client.route('/subscriber_status')
def subscriber_status():
    session_id = getID()
    data = dict(subscriber_inbox.get(session_id, {"windows": {}}))

    row_res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('q_number, topic')
        .eq('id', session_id)
        .limit(1)
    )

    if row_res.data:
        q_number = row_res.data[0]['q_number']
        q_type = row_res.data[0]['topic']
        session['q_number'] = q_number
        session['topic'] = q_type
        ahead_res = execute_with_retry(
            supabase.table(QUEUE_TABLE)
            .select('id', count='exact')
            .eq('topic', q_type)
            .lt('q_number', q_number)
        )
        number_infront = ahead_res.count or 0
        data["my_q_number"] = int(q_number)
        data["number_infront"] = number_infront
        data["wait_time"] = number_infront * 3
    elif session.get('q_number') is not None:
        data["my_q_number"] = int(session.get('q_number'))
        data["number_infront"] = 0
        data["wait_time"] = 0

    return jsonify(data)


@client.route('/your_turn')
def your_turn():
    session_id = getID()
    inbox_data = subscriber_inbox.get(session_id, {})
    windows_data = inbox_data.get("windows", {})
    topic = inbox_data.get("topic") or session.get("topic") or "CASHIER"

    row_res = execute_with_retry(
        supabase.table(QUEUE_TABLE)
        .select('q_number, topic')
        .eq('id', session_id)
        .limit(1)
    )

    if row_res.data:
        ticket_number = row_res.data[0]['q_number']
        topic = row_res.data[0]['topic']
        session['q_number'] = ticket_number
        session['topic'] = topic
    else:
        ticket_number = session.get('q_number')

    serving_window = None
    if ticket_number is not None:
        for win_num, info in windows_data.items():
            if isinstance(info, dict) and info.get("serving") == int(ticket_number):
                serving_window = win_num
                break

        # Fallback directly to SERVING table if broker inbox wasn't populated yet
        if serving_window is None:
            serving_res = execute_with_retry(
                supabase.table(SERVING_TABLE)
                .select('window')
                .eq('topic', topic)
                .eq('q_number', int(ticket_number))
                .limit(1)
            )
            if serving_res.data:
                serving_window = serving_res.data[0]['window']

    prefix = "REG" if topic == "REGISTRAR" else "CASH"
    office_label = topic.capitalize()
    served_at = now_manila().strftime("%Y-%m-%d %I:%M:%S %p")

    return render_template(
        'your_turn.html',
        office_label=office_label,
        prefix=prefix,
        q_number=f"{int(ticket_number):03d}" if ticket_number is not None else "---",
        serving_window=serving_window if serving_window is not None else "-",
        served_at=served_at,
    )


# EXIT FROM THE LINE
@client.route('/leave')
def leave_queue():
    session_id = getID()

    print('MESSAGE: You have left the queue.')

    execute_with_retry(
        supabase.table(QUEUE_TABLE).delete().eq('id', session_id)
    )
    subscriber_inbox.pop(session_id, None)
    session.pop('session_id', None)
    session.pop('q_number', None)
    session.pop('topic', None)

    return redirect(url_for('client.home'))