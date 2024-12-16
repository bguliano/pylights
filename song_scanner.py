import base64
import json
import re
from pathlib import Path
from typing import Optional

import mutagen.mp3

from common import Song, VIXEN_DIR


class SongScanner:
    def __init__(self, vixen_dir: Path):
        self.vixen_dir = vixen_dir
        assert self.vixen_dir.exists()
        assert self.vixen_dir.name == 'Vixen 3'

    def _create_song(self, tim_file: Path) -> Optional[Song]:
        fseq_dir = self.vixen_dir / 'Export'
        mp3_dir = self.vixen_dir / 'Media'

        # first, discover name of mp3 file using .tim file
        xml_contents = tim_file.read_text()
        match = re.search(r'\b[\w\-(). ]+\.mp3\b', xml_contents, re.IGNORECASE)

        # if there is no song, then skip it (test sequence)
        if not match:
            return None
        mp3_filename = match.group(0)

        # next, make sure the mp3 file and fseq file actually exist
        if not (mp3_file := mp3_dir / mp3_filename).exists():
            return None
        if not (fseq_file := fseq_dir / (tim_file.stem + '.fseq')).exists():
            return None

        # get song info path for extracting metadata and image
        song_info_path = Path('song_info')
        title = tim_file.stem

        # if the song is marked as exclude, don't create a Song object
        if (song_info_path / title).with_suffix('.exclude').exists():
            return None

        # get artist and other metadata if available
        song_info_json = json.loads((song_info_path / 'song_info.json').read_text())
        if metadata := song_info_json.get(title):
            artist = metadata.get('artist') or 'Unknown Artist'
        else:
            artist = 'Unknown Artist'

        # get album art if available
        image_file = (song_info_path / title).with_suffix('.jpg')
        if image_file.exists():
            album_art = base64.b64encode(image_file.read_bytes()).decode('utf-8')
        else:
            album_art = ''

        # get length of the song
        length = mutagen.mp3.MP3(mp3_file).info.length * 1000

        # then, create the Song object and return it
        return Song(
            title=title,
            tim_file=tim_file,
            mp3_file=mp3_file,
            fseq_file=fseq_file,
            artist=artist,
            album_art=album_art,
            length_ms=length
        )

    def scan(self) -> dict[str, Song]:
        seq_dir = self.vixen_dir / 'Sequence'
        # use walrus operator to create flatmap within dict comprehension
        return {
            song.title: song for tim_file in seq_dir.glob('[!.]*.tim')
            if (song := self._create_song(tim_file))
        }


if __name__ == '__main__':
    song_dict = SongScanner(VIXEN_DIR).scan()
