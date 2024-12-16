import json
import socket
import time
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Thread, Event
from typing import Iterator, Optional

import mutagen.mp3
import psutil
import pygame

from common import Song, VIXEN_DIR, SongsDescriptor, SongDescriptor, LightsDescriptor, \
    LightDescriptor, PresetsDescriptor, PresetDescriptor, RemapDescriptor, DeveloperDescriptor, VERSION, InfoDescriptor, \
    ZERO_IP
from fseq_parser import FSEQParser
from relay_reference import relay_reference, Relay
from show_file_generator import generate_all_show_files
from song_scanner import SongScanner
from zero_manager import upload_shows, start_led_server, send_led_server_command, LEDServerCommand, \
    check_led_server_running


class _ImplementsGetInfo(ABC):
    @abstractmethod
    def get_info(self) -> None:
        pass


# ------------------------------------------------------------------------------------------------


class _SongsController(_ImplementsGetInfo):
    def __init__(self, vixen_dir: Path):
        self.songs = SongScanner(vixen_dir).scan()

        pygame.mixer.init()
        self.current_song: Optional[Song] = None
        self.song_thread: Optional[Thread] = None
        self.song_thread_stop = Event()
        self.paused = True

    def _threaded_relay_play(self, song: Song):
        parser = FSEQParser(song.fseq_file)
        while not self.song_thread_stop.is_set():
            current_ms = max(0, pygame.mixer.music.get_pos() - 150)
            data = parser.get_frame_at_ms(current_ms)
            assert len(data.relay_bytes) == len(relay_reference.mapping)
            for relay_byte, relay in zip(data.relay_bytes, relay_reference.relays):
                relay.value = bool(relay_byte)
            if not pygame.mixer.music.get_busy() and not self.paused:
                # this means the audio file has ended, so stop this thread from another thread
                # set the thread so that it doesn't call stop again
                self.song_thread_stop.set()
                Thread(target=self.stop).start()

    def play(self, song_name: str) -> SongsDescriptor:
        # if a song is already playing, stop it
        if self.current_song is not None:
            self.stop()

        # get Song object
        song = self.songs[song_name]
        self.current_song = song

        # start loading the show on the pi zero
        start_led_server(song.show_file)

        # reset pygame.mixer to allow for frequency change
        old_volume = self.volume
        pygame.mixer.quit()

        # init pygame.mixer using mp3 file's frequency and set its volume back to what it was before
        freq = mutagen.mp3.MP3(song.mp3_file).info.sample_rate
        pygame.mixer.init(frequency=freq)
        self.volume = old_volume

        # prep the song to play
        pygame.mixer.music.load(song.mp3_file)
        self.song_thread_stop.clear()
        self.song_thread = Thread(target=self._threaded_relay_play, args=(song,))
        self.paused = False

        # wait for led_server to be ready (about 1 second) and play!
        time.sleep(1)
        send_led_server_command(LEDServerCommand.PLAY)
        time.sleep(0.1)  # 100ms sync with pygame
        pygame.mixer.music.play()
        self.song_thread.start()

        return self.get_info()

    def pause(self) -> SongsDescriptor:
        self.paused = True
        pygame.mixer.music.pause()
        send_led_server_command(LEDServerCommand.PAUSE)

        return self.get_info()

    def resume(self) -> SongsDescriptor:
        self.paused = False
        pygame.mixer.music.unpause()
        send_led_server_command(LEDServerCommand.RESUME)

        return self.get_info()

    def stop(self) -> SongsDescriptor:
        self.paused = True
        self.current_song = None
        pygame.mixer.music.stop()
        send_led_server_command(LEDServerCommand.STOP)  # will automatically turn off LED strips
        self.song_thread_stop.set()
        self.song_thread.join()
        relay_reference.all_off()

        return self.get_info()

    @property
    def volume(self) -> int:
        return int(pygame.mixer.music.get_volume() * 100)

    @volume.setter
    def volume(self, value: int) -> None:
        if value < 0 or value > 100:
            print(f'Invalid volume: {value}, it will be ignored')
            return

        pygame.mixer.music.set_volume(value / 100)

    @staticmethod
    def _song_to_song_descriptor(song: Song) -> SongDescriptor:
        return SongDescriptor(
            title=song.title,
            artist=song.artist,
            album_art=song.album_art,
            length_ms=song.length_ms
        )

    def get_info(self) -> SongsDescriptor:
        if self.current_song is None:
            playing = None
        else:
            playing = self._song_to_song_descriptor(self.current_song)

        return SongsDescriptor(
            songs=[self._song_to_song_descriptor(song) for song in self.songs.values()],
            playing=playing,
            paused=self.paused,
            current_time_ms=max(0.0, pygame.mixer.music.get_pos()),
            volume=self.volume
        )


class _LightsController(_ImplementsGetInfo):
    def all_on(self) -> LightsDescriptor:
        relay_reference.all_on()

        return self.get_info()

    def all_off(self) -> LightsDescriptor:
        relay_reference.all_off()

        return self.get_info()

    def turn_on(self, light_name: str) -> LightsDescriptor:
        relay_reference.mapping[light_name].on()

        return self.get_info()

    def turn_off(self, light_name: str) -> LightsDescriptor:
        relay_reference.mapping[light_name].off()

        return self.get_info()

    def toggle(self, light_name: str) -> LightsDescriptor:
        relay_reference.mapping[light_name].toggle()

        return self.get_info()

    def get_info(self) -> LightsDescriptor:
        return LightsDescriptor(
            lights=[
                LightDescriptor(name=name, gpio=relay.pin.number, value=relay.value)
                for name, relay in relay_reference.mapping.items()
            ]
        )


class _PresetController(_ImplementsGetInfo):
    CONFIG_PATH = Path('config/presets.json')

    def __init__(self):
        self.presets: dict[str, list[str]] = json.loads(self.CONFIG_PATH.read_text())

    def _save(self) -> None:
        self.CONFIG_PATH.write_text(json.dumps(self.presets))

    def activate(self, preset_name: str) -> PresetsDescriptor:
        light_names = self.presets[preset_name]

        # turn off all relays and turn on only the lights in the preset
        relay_reference.all_off()
        for light_name in light_names:
            relay_reference.mapping[light_name].on()

        return self.get_info()

    def add(self, preset_name: str, light_names: list[str]) -> PresetsDescriptor:
        self.presets[preset_name] = light_names
        self._save()

        return self.get_info()

    def get_info(self) -> PresetsDescriptor:
        return PresetsDescriptor(
            presets=[
                PresetDescriptor(name=name, lights=light_names)
                for name, light_names in self.presets.items()
            ]
        )


class RemapNameDoesNotExist(Exception):
    def __init__(self, name: str):
        super().__init__(f'No light found with name: {name}')


class _RemapController(_ImplementsGetInfo):
    def __init__(self):
        self.remap: Optional[dict[str, Optional[int]]] = None
        self.relay_iterator: Optional[Iterator] = None
        self.current_relay: Optional[Relay] = None

    def start(self) -> RemapDescriptor:
        if self.remap is not None:
            self._stop()

        # init remap vars
        self.remap = {
            key: None
            for key in relay_reference.mapping.keys()
        }
        self.relay_iterator = iter(relay_reference.relays)

        # show first relay
        relay_reference.all_off()
        self.current_relay = next(self.relay_iterator)
        self.current_relay.on()

        return self.get_info()

    def next(self, assign_light_name: str) -> RemapDescriptor:
        if assign_light_name not in relay_reference.mapping:
            raise RemapNameDoesNotExist(assign_light_name)

        # assign pin of light name to remap
        self.remap[assign_light_name] = self.current_relay.pin.number

        # turn off current relay and turn on next
        self.current_relay.off()
        try:
            self.current_relay = next(self.relay_iterator)
            self.current_relay.on()
        except StopIteration:
            self._stop()

        return self.get_info()

    def cancel(self) -> RemapDescriptor:
        if self.remap is not None:
            self._stop()

        return self.get_info()

    def _stop(self) -> None:
        self.relay_iterator = None
        self.current_relay = None
        relay_reference.all_off()

        # save only if remap is complete
        if all(self.remap.values()):
            json_data = json.dumps(self.remap)
            relay_reference.CONFIG_PATH.write_text(json_data)
            relay_reference.reload()

        self.remap = None

    def get_info(self) -> RemapDescriptor:
        if self.remap is None:
            remaining = None
        else:
            remaining = [key for key, value in self.remap.items() if value is None]

        return RemapDescriptor(
            remaining=remaining
        )


class _DeveloperController(_ImplementsGetInfo):
    def __init__(self, vixen_dir: Path):
        self.vixen_dir = vixen_dir

    def recompile_shows(self) -> DeveloperDescriptor:
        # all_show_files = generate_all_show_files()
        # upload_shows(all_show_files)
        time.sleep(3)

        return self.get_info()

    def info(self) -> DeveloperDescriptor:
        return self.get_info()

    def get_info(self) -> DeveloperDescriptor:
        def get_ip() -> str:
            try:
                # Establish a temporary connection to a known external host
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    # Connecting to an external server (Google DNS server here)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                return local_ip
            except Exception as e:
                return f"Unable to determine IP: {e}"

        return DeveloperDescriptor(
            version=VERSION,
            ip_address=get_ip(),
            cpu_usage=psutil.cpu_percent(1),
            led_server_ip_address=ZERO_IP,
            led_server_status=check_led_server_running()
        )


# ------------------------------------------------------------------------------------------------


class PylightsController(_ImplementsGetInfo):
    def __init__(self, vixen_dir: str):
        self.vixen_dir = Path(vixen_dir)

        # add controller modules
        self.songs = _SongsController(self.vixen_dir)
        self.lights = _LightsController()
        self.presets = _PresetController()
        self.remap = _RemapController()
        self.developer = _DeveloperController(self.vixen_dir)

    def get_info(self) -> InfoDescriptor:
        return InfoDescriptor(
            songs=self.songs.get_info(),
            lights=self.lights.get_info(),
            presets=self.presets.get_info()
        )


# ------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    c = PylightsController(VIXEN_DIR)
