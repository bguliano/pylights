from dataclasses import dataclass, field
from pathlib import Path

from constants import NUM_BYTES_TOTAL, NUM_BYTES_RELAYS, NUM_BYTES_L


@dataclass
class Song:
    path: Path
    mp3_file: Path
    fseq_file: Path

    @property
    def title(self) -> str:
        return self.path.stem


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
