from pathlib import Path

from fseq_parser import FSEQParser
from objects import Song
from vixen_scanner import VixenScanner


class _PartTracker:
    def __init__(self, prefix: str):
        self.instructions_file = Path(f'{prefix}_instructions.show')
        self.part_file = Path(f'{prefix}_parts.show')

        self.num_waits: list[int] = [0]
        self.byte_stream: list[bytes] = [bytes()]

    def new_bytes(self, b: bytes):
        if b == self.byte_stream[-1]:
            self.num_waits[-1] += 1
        else:
            self.byte_stream.append(b)
            if self.num_waits[-1] != 0:
                self.num_waits.append(0)

    def save_to_files(self):
        instructions = b'\n'.join((x.to_bytes((x.bit_length() + 7) // 8, 'big') for x in self.num_waits))
        self.instructions_file.write_bytes(instructions)
        del self.byte_stream[0]
        self.part_file.write_bytes(b'\n'.join(self.byte_stream))


def generate_show_file(song: Song):
    parser = FSEQParser(song.fseq_file)

    l_part = _PartTracker('l')
    r_part = _PartTracker('r')

    for frame in parser.iter_frames():
        l_part.new_bytes(frame.light_strip_l_bytes)
        r_part.new_bytes(frame.light_strip_r_bytes)

    l_part.save_to_files()
    r_part.save_to_files()


if __name__ == '__main__':
    scanner = VixenScanner('/Volumes/USBX/Vixen 3')
    scanner.scan()
    generate_show_file(scanner.songs[1])
