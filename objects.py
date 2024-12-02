from dataclasses import dataclass, field
from pathlib import Path


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
        # light_strip_l_bytes = 563 LEDs  x 3 bytes/LED  = 1689 bytes
        #                                                = 3367 bytes total
        assert len(self.raw_bytes) == 3367

        self.relay_bytes = self.raw_bytes[:16]
        self.light_strip_l_bytes = self.raw_bytes[16:1662]
        self.light_strip_r_bytes = self.raw_bytes[1662:]
