from pathlib import Path

from fseq_parser import FSEQParser
from objects import Song


class InoGenerator:
    def __init__(self):
        self._template = Path('template.ino').read_text()

    def from_song(self, song: Song) -> :


def generate_ino(song: Song):
    parser = FSEQParser(song.fseq_file)
    for ms in range(parser.song_length_ms):

