from pathlib import Path

from fseq_parser import FSEQParser
from objects import Song


def generate_show_file(song: Song):
    parser = FSEQParser(song.fseq_file)
    for ms in range(parser.song_length_ms):

