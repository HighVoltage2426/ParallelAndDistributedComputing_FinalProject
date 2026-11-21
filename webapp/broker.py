class Broker:
    def __init__(self):
        self.subscribers = {}
        self.topic_state = {}  
        self.subscribed_ids = set()

    def subscribe(self, topic, callback, subscriber_id=None):
        if topic not in self.subscribers:
            self.subscribers[topic] = []

        sub_key = (topic, subscriber_id)
        if subscriber_id is None or sub_key not in self.subscribed_ids:
            self.subscribers[topic].append(callback)
            if subscriber_id is not None:
                self.subscribed_ids.add(sub_key)

        if topic in self.topic_state:
            callback(self.topic_state[topic])

    def publish(self, topic, message):
        self.topic_state[topic] = message
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                callback(message)

broker = Broker()