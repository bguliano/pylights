import socket
from enum import StrEnum
from pathlib import Path

from fabric import Connection
from humanize import naturalsize


def get_led_server_ip() -> str:
    return socket.gethostbyname('pylightszero.local')


class _ZeroClient(Connection):
    def __init__(self):
        ssh_key_file = Path('~/.ssh/pylightszero_key').expanduser()
        super().__init__(
            host=get_led_server_ip(),
            user='pylightszero',
            connect_kwargs={'key_filename': str(ssh_key_file)}
        )


_ZERO_IP = get_led_server_ip()
_ZERO_PORT = 12345


class LEDServerCommand(StrEnum):
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    RESUME = 'RESUME'
    STOP = 'STOP'


def _upload_show(zc: _ZeroClient, show_file: Path, current: int, total: int):
    file_size = show_file.stat().st_size
    print(f'Uploading show "{show_file.stem}" of size {naturalsize(file_size)}...', end='', flush=True)
    zc.put(show_file, '/home/pylightszero/shows')
    print(f'Done ({current}/{total})')


def upload_shows(show_files: list[Path]) -> None:
    with _ZeroClient() as zc:
        for i, show_file in enumerate(show_files, 1):
            _upload_show(zc, show_file, i, len(show_files))


def start_led_server(show_file: Path) -> None:
    cmd = f'sudo ./led_server "shows/{show_file.name}" &'
    print(f'Running command: {cmd}...', end='', flush=True)
    with _ZeroClient() as zc:
        zc.run(cmd, disown=True)
    print('Done')


def send_led_server_command(command: LEDServerCommand) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((_ZERO_IP, _ZERO_PORT))
            s.sendall(command.encode())
            print(f'Subcommand "{command}" sent successfully.')
    except ConnectionRefusedError:
        print('Could not connect to led_server. Ensure it is running.')


def check_led_server_running() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((_ZERO_IP, _ZERO_PORT))
            return True
    except ConnectionRefusedError:
        return False


if __name__ == '__main__':
    upload_shows([Path('shows/Carol of the Bells.show')])
    # start_led_server(Path('shows/Carey Grinch.show'))
