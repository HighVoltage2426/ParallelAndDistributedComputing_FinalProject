
def subscriber(message):
    print(f"[{message['topic']} SUBSCRIBER] Received notification: Ticket REG-{message['queue_number']} is now in line!")