import time
from pathlib import Path

from umqtt.simple import MQTTClient


# Received messages from subscriptions will be delivered to this callback
def sub_cb(topic, msg):
    print((topic, msg))


class Client(MQTTClient):
    def __init__(self):
        super().__init__('pico_client', 'localhost')
        self.set_callback(self.callback_func)

    def callback_func(self, topic: str, msg: str):
        print(f"Received message: {topic} - {msg}")


class LightShow:
    def __init__(self):
        self.client = MQTTClient('pico_client', 'mqtt.eclipseprojects.io')
        self.client.connect()
        self.shows = list(Path('shows').glob('*.show'))


def main(server="localhost"):
    c = MQTTClient("umqtt_client", server)
    c.set_callback(sub_cb)
    c.connect()
    c.subscribe(b"foo_topic")
    while True:
        if True:
            # Blocking wait for message
            c.wait_msg()
        else:
            # Non-blocking wait for message
            c.check_msg()
            # Then need to sleep to avoid 100% CPU usage (in a real
            # app other useful actions would be performed instead)
            time.sleep(1)

    c.disconnect()


if __name__ == "__main__":
    main()