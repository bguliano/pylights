import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---- Constants ---------------------------------------------------------------------------------

VERSION = '1.0.1'

NUM_LEDS_L = 554
NUM_LEDS_R = 563

NUM_BYTES_RELAYS = 16
NUM_BYTES_L = NUM_LEDS_L * 3
NUM_BYTES_R = NUM_LEDS_R * 3
NUM_BYTES_TOTAL = NUM_BYTES_RELAYS + NUM_BYTES_L + NUM_BYTES_R

VIXEN_DIR = Path('Vixen 3')
DEBUG_VIXEN_SAMPLE_FSEQ_PATH = Path('Vixen 3/Export/Carey Grinch.fseq')

try:
    ZERO_IP = socket.gethostbyname('pylightszero.local')
except socket.gaierror:
    print('Debugging mode active; pylightszero control disabled')
    ZERO_IP = ''
ZERO_PORT = 12345


# ------------------------------------------------------------------------------------------------


# ---- Objects -----------------------------------------------------------------------------------

@dataclass
class Song:
    title: str
    tim_file: Path
    mp3_file: Path
    fseq_file: Path
    artist: str
    album_art: str
    length_ms: float

    @property
    def show_file(self) -> Path:
        # this is an assumed path, it does not necessarily exist when the Song object is created
        return (Path('shows') / self.title).with_suffix('.show')


@dataclass
class FSEQFrame:
    raw_bytes: bytes

    relay_bytes: bytes = field(init=False)
    light_strip_l_bytes: bytes = field(init=False)
    light_strip_r_bytes: bytes = field(init=False)

    def __post_init__(self):
        # relay_bytes         = 16 relays x 1 byte/relay = 16 bytes
        # light_strip_l_bytes = 554 LEDs  x 3 bytes/LED  = 1662 bytes
        # light_strip_r_bytes = 563 LEDs  x 3 bytes/LED  = 1689 bytes
        #                                                = 3367 bytes total
        assert len(self.raw_bytes) == NUM_BYTES_TOTAL

        self.relay_bytes = self.raw_bytes[:NUM_BYTES_RELAYS]
        self.light_strip_l_bytes = self.raw_bytes[NUM_BYTES_RELAYS:NUM_BYTES_RELAYS + NUM_BYTES_L]
        self.light_strip_r_bytes = self.raw_bytes[NUM_BYTES_RELAYS + NUM_BYTES_L:]


@dataclass
class SongDescriptor:
    title: str
    artist: str
    album_art: str
    length_ms: float


@dataclass
class SongsDescriptor:
    songs: list[SongDescriptor]
    playing: Optional[SongDescriptor]
    paused: bool
    current_time_ms: float
    volume: int  # 0-100


@dataclass
class LightDescriptor:
    name: str
    gpio: int
    value: bool


@dataclass
class LightsDescriptor:
    lights: list[LightDescriptor]


@dataclass
class PresetDescriptor:
    name: str
    lights: list[str]


@dataclass
class PresetsDescriptor:
    presets: list[PresetDescriptor]


@dataclass
class RemapDescriptor:
    remaining: Optional[list[str]]


@dataclass
class DeveloperDescriptor:
    version: str
    ip_address: str
    cpu_usage: float
    led_server_ip_address: str
    led_server_status: bool


@dataclass
class InfoDescriptor:
    songs: SongsDescriptor
    lights: LightsDescriptor
    presets: PresetsDescriptor


# ------------------------------------------------------------------------------------------------


# ---- Functions ---------------------------------------------------------------------------------

def print_progress(message: str) -> None:
    print(message, end='', flush=True)


def print_done() -> None:
    print('Done')

# ------------------------------------------------------------------------------------------------
