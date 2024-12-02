from pathlib import Path

import zstandard as zstd

from objects import FSEQFrame


class ParserError(Exception):
    pass


def int_from_bytes(b: bytes) -> int:
    return int.from_bytes(b, 'little')


def compression_type_from_num(n: int) -> str:
    if n == 0:
        return 'none'
    if n == 1:
        return 'zstd'
    if n == 2:
        return 'gzip'
    raise ParserError(f'unrecognized compression type: {n}')


class FSEQParser:
    def __init__(self, file: Path):
        self.file = file.open('rb')

        magic = self.file.read(4)
        if magic != b'PSEQ':
            raise ParserError(f'invalid fseq file magic: {magic}')

        channel_data_start = int_from_bytes(self.file.read(2))

        minor_version = int_from_bytes(self.file.read(1))
        major_version = int_from_bytes(self.file.read(1))

        version = (major_version, minor_version)
        if version != (2, 0):
            raise ParserError(f'unrecognized fseq file version: {version}')

        _ = int_from_bytes(self.file.read(2))  # standard_header_length

        self.channel_count_per_frame = int_from_bytes(self.file.read(4))

        self.number_of_frames = int_from_bytes(self.file.read(4))

        self.step_time_in_ms = int_from_bytes(self.file.read(1))

        bit_flags = int_from_bytes(self.file.read(1))
        if bit_flags != 0:
            raise ParserError(f'unrecognized bit flags: {bit_flags}')

        self.compression_type = compression_type_from_num(int_from_bytes(self.file.read(1)))
        if self.compression_type == 'gzip':
            raise ParserError(f'unsupported compression type: {self.compression_type}')

        num_compression_blocks = int_from_bytes(self.file.read(1))
        num_sparse_ranges = int_from_bytes(self.file.read(1))

        bit_flags = int_from_bytes(self.file.read(1))
        if bit_flags != 0:
            raise ParserError(f'unrecognized bit flags: {bit_flags}')

        _ = self.file.read(8)  # unique_id

        offset = channel_data_start
        self.frame_offsets = []
        if self.compression_type == 'none':
            self.frame_offsets.append((0, offset))
        for i in range(num_compression_blocks):
            frame_number = int_from_bytes(self.file.read(4))
            length_of_block = int_from_bytes(self.file.read(4))

            if length_of_block > 0:
                self.frame_offsets.append((frame_number, offset))
                offset += length_of_block
        self.frame_offsets.append((self.number_of_frames, offset))

        sparse_ranges = []
        for i in range(num_sparse_ranges):
            start_channel_number = int_from_bytes(self.file.read(3))
            number_of_channels = int_from_bytes(self.file.read(3))
            sparse_ranges.append((start_channel_number, number_of_channels))

        variable_headers = []
        start = self.file.tell()

        while start < channel_data_start - 4:
            length = int_from_bytes(self.file.read(2))
            if length == 0:
                break

            vheader_code = self.file.read(2).decode('ascii')
            vheader_data = self.file.read(length - 4)
            variable_headers.append((vheader_code, vheader_data))

            start += length

        self.song_length_ms = self.number_of_frames * self.step_time_in_ms

    def __del__(self):
        try:
            self.file.close()
        except AttributeError:
            pass  # the file was never opened because of FileNotFoundError

    def get_frame_at_index(self, frame_index: int) -> FSEQFrame:
        if frame_index >= self.number_of_frames:
            raise ValueError('frame index out of bounds')

        current_block = 0
        while frame_index >= self.frame_offsets[current_block + 1][0]:
            current_block += 1

        offset = self.frame_offsets[current_block][1]
        self.file.seek(offset, 0)

        if self.compression_type == 'zstd':
            dctx = zstd.ZstdDecompressor()

            length = self.frame_offsets[current_block + 1][1] - self.frame_offsets[current_block][1]
            block = self.file.read(length)
            block = dctx.stream_reader(block).readall()

            fidx = (frame_index - self.frame_offsets[current_block][0]) * self.channel_count_per_frame
        else:
            block = self.file.read()
            fidx = frame_index * self.channel_count_per_frame

        data = block[fidx:fidx + self.channel_count_per_frame]
        return FSEQFrame(data)

    def get_frame_at_ms(self, milliseconds: int) -> FSEQFrame:
        return self.get_frame_at_index(milliseconds // self.step_time_in_ms)


if __name__ == '__main__':
    fseq_file = Path('/Volumes/USBX/Vixen 3/Export/Carey Grinch.fseq')
    parser = FSEQParser(fseq_file)
    pass
