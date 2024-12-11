import struct
from pathlib import Path

from common import Song, NUM_BYTES_L, NUM_BYTES_R, DEBUG_VIXEN_DIR
from fseq_parser import FSEQParser
from vixen_scanner import VixenScanner


class _ShowFileGenerator:
    def __init__(self, bytes_left: int, bytes_right: int, frame_delay_ms: int):
        if bytes_left % 3 != 0:
            raise ValueError('Bytes for left side must be divisible by 3 to represent RGB values.')
        if bytes_right % 3 != 0:
            raise ValueError('Bytes for right side must be divisible by 3 to represent RGB values.')

        self.bytes_left: int = bytes_left
        self.bytes_right: int = bytes_right
        self.frame_delay_ms: int = frame_delay_ms
        self.left_frames: list[bytes] = []
        self.right_frames: list[bytes] = []

    def add_frame(self, left_frame: bytes, right_frame: bytes) -> None:
        if len(left_frame) != self.bytes_left:
            raise ValueError(f'Left frame must have exactly {self.bytes_left} bytes.')
        if len(right_frame) != self.bytes_right:
            raise ValueError(f'Right frame must have exactly {self.bytes_right} bytes.')

        self.left_frames.append(left_frame)
        self.right_frames.append(right_frame)

    def write_to_file(self, output_filename: str) -> Path:
        assert len(self.left_frames) == len(self.right_frames), \
            'Left and right frame lists must have the same number of frames.'

        output_path = (Path('shows') / output_filename).with_suffix('.show')
        with output_path.open('wb') as f:
            f.write(struct.pack('I', self.frame_delay_ms))
            for left_frame, right_frame in zip(self.left_frames, self.right_frames):
                for i in range(0, len(left_frame), 3):
                    r, g, b = left_frame[i], left_frame[i + 1], left_frame[i + 2]
                    f.write(struct.pack('I', (r << 16) | (g << 8) | b))
                for i in range(0, len(right_frame), 3):
                    r, g, b = right_frame[i], right_frame[i + 1], right_frame[i + 2]
                    f.write(struct.pack('I', (r << 16) | (g << 8) | b))

        return output_path


def generate_show_file(song: Song) -> Path:
    # parse the song file using FSEQParser and create a _ShowFileGenerator
    parser = FSEQParser(song.fseq_file)
    show_generator = _ShowFileGenerator(
        NUM_BYTES_L,
        NUM_BYTES_R,
        parser.step_time_in_ms
    )

    # iterate over frames of the song, adding to the _ShowFileGenerator each time
    for frame in parser.iter_frames():
        show_generator.add_frame(frame.light_strip_l_bytes, frame.light_strip_r_bytes)

    # write the show file to disk and return the Path object of the file
    return show_generator.write_to_file(song.title)


if __name__ == '__main__':
    all_songs = VixenScanner(DEBUG_VIXEN_DIR).scan()
    all_show_files = [generate_show_file(song) for song in all_songs]
