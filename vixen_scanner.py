import re
from pathlib import Path

from objects import Song


class VixenScanner:
    def __init__(self, vixen_dir: str):
        self.vixen_dir = Path(vixen_dir)
        assert self.vixen_dir.exists()
        assert self.vixen_dir.name == 'Vixen 3'
        self.songs: list[Song] | None = None

    def _create_song(self, tim_file: Path) -> Song | None:
        fseq_dir = self.vixen_dir / 'Export'
        mp3_dir = self.vixen_dir / 'Media'

        # first, discover name of mp3 file using .tim file
        xml_contents = tim_file.read_text()
        match = re.search(r'\b[\w\-(). ]+\.mp3\b', xml_contents, re.IGNORECASE)

        # if there is no song, then skip it (test sequence)
        if not match:
            return None
        mp3_filename = match.group(0)

        # then, create the Song object and return it
        return Song(
            path=tim_file,
            mp3_file=mp3_dir / mp3_filename,
            fseq_file=fseq_dir / (tim_file.stem + '.fseq')
        )

    def scan(self) -> None:
        seq_dir = self.vixen_dir / 'Sequence'
        # use walrus operator to create flatmap within list creation
        self.songs = [
            song for tim_file in seq_dir.glob('[!.]*.tim')
            if (song := self._create_song(tim_file))
        ]


if __name__ == '__main__':
    scanner = VixenScanner('/Volumes/USBX/Vixen 3')
    scanner.scan()
