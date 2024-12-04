import board
import socketpool
import struct
import time
import wifi
import ipaddress
import random
import supervisor
from adafruit_neopxl8 import NeoPxl8, RGB


supervisor.runtime.autoreload = False


class ServerNotConnectedException(Exception):
    pass


class Client:
    def __init__(self, num_pixels: int):
        self.num_bytes = num_pixels * 3
        self._buffer = bytearray(self.num_bytes)

        self.pool = socketpool.SocketPool(wifi.radio)
        self.server_socket: Optional[socketpool.Socket] = None

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        if self.server_socket is not None:
            self.server_socket.close()

    @property
    def connected(self) -> bool:
        return self.server_socket is not None

    def connect(self, host: str, port: int, *, wait_time: int = 1):
        while True:
            sock = self.pool.socket(
                socketpool.SocketPool.AF_INET, socketpool.SocketPool.SOCK_STREAM
            )
            try:
                sock.connect((host, port))
            except OSError:
                print("Connect failed, retrying")
                sock.close()
                del sock
                time.sleep(wait_time)
            else:
                self.server_socket = sock
                break

    def get_light_data(self):
        # check if connected to server
        if not self.connected:
            raise ServerNotConnectedException()
        
        bytes_read = 0
        view = memoryview(self._buffer)
        while bytes_read < self.num_bytes:
            to_read = self.num_bytes - bytes_read
            bytes_read += self.server_socket.recv_into(view[bytes_read:], to_read)
        
        return list(view)


def connect_to_wifi(ssid: str, password: str):
    print("Connecting to wifi")
    wifi.radio.connect(ssid, password)
    print(f"Self IP: {wifi.radio.ipv4_address}")
    

strand_lengths = [554, 563]

num_pixels = max(strand_lengths) * len(strand_lengths)

# Make the object to control the pixels
pixels = NeoPxl8(
    board.GP0,
    num_pixels,
    num_strands=len(strand_lengths),
    auto_write=False,
    brightness=0.2,
    pixel_order=RGB
)

# connect_to_wifi("rpi01", "7Gw3>6bdy0[8&ZVB")
connect_to_wifi("LEXINGTON", "JETSrule99")

client = Client(num_pixels)
# client.connect("10.42.0.1", 1234)
client.connect("192.168.1.45", 1234)

# clear all strips
pixels.fill(0)
pixels.show()

while True:
    data = client.get_light_data()
    # print(len(data))
    # print(len(list(filter(lambda x: x == 255, data))))
    # print(set(data))
    # print(data)
    # assert len(set(data)) == 1
    # rand_color = [random.randint(0, 255) for _ in range(3)]
    pixels[:] = data
    pixels.show()
