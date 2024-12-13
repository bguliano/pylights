import json
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Thread, Event
from typing import Iterator

import mutagen.mp3
import pygame

from common import Song, print_progress, print_done, DEBUG_VIXEN_DIR
from fseq_parser import FSEQParser
from relay_reference import relay_reference, Relay
from show_file_generator import generate_show_file
from vixen_scanner import VixenScanner
from zero_manager import upload_shows, start_led_server, send_led_server_command, LEDServerCommand, \
    check_led_server_running


class _ControllerModule(ABC):
    @abstractmethod
    def get_info(self) -> None:
        pass


# ------------------------------------------------------------------------------------------------


class _SongsController(_ControllerModule):
    def __init__(self, vixen_dir: Path):
        self.songs = VixenScanner(vixen_dir).scan()

        pygame.mixer.init()
        self.song_thread: Thread | None = None
        self.song_thread_stop = Event()

    def _threaded_relay_play(self, song: Song):
        parser = FSEQParser(song.fseq_file)
        while not self.song_thread_stop.is_set():
            current_ms = max(0, pygame.mixer.music.get_pos() - 150)
            data = parser.get_frame_at_ms(current_ms)
            assert len(data.relay_bytes) == len(relay_reference.mapping)
            for relay_byte, relay in zip(data.relay_bytes, relay_reference.relays):
                relay.value = bool(relay_byte)

    @property
    def playing(self) -> bool:
        # perform two checks to ensure we are or are not playing
        return pygame.mixer.music.get_busy() or check_led_server_running()

    def play(self, song_name: str) -> None:
        # if a song is already playing, stop it
        if self.playing:
            self.stop()

        # get Song object
        song = self.songs[song_name]

        # start loading the show on the pi zero
        start_led_server(song.show_file)

        # reset pygame.mixer to allow for frequency change
        old_volume = self.get_volume()
        pygame.mixer.quit()

        # init pygame.mixer using mp3 file's frequency and set its volume back to what it was before
        freq = mutagen.mp3.MP3(song.mp3_file).info.sample_rate
        pygame.mixer.init(frequency=freq)
        self.set_volume(old_volume)

        # finally, load the mp3 file and play
        pygame.mixer.music.load(song.mp3_file)
        pygame.mixer.music.play()
        self.song_thread_stop.clear()
        self.song_thread = Thread(target=self._threaded_relay_play, args=(song,))
        self.song_thread.start()
        send_led_server_command(LEDServerCommand.PLAY)

    def pause(self) -> None:
        pygame.mixer.music.pause()
        send_led_server_command(LEDServerCommand.PAUSE)

    def resume(self) -> None:
        pygame.mixer.music.unpause()
        send_led_server_command(LEDServerCommand.RESUME)

    def stop(self) -> None:
        pygame.mixer.music.stop()
        send_led_server_command(LEDServerCommand.STOP)  # will automatically turn off LED strips
        self.song_thread_stop.set()
        self.song_thread.join()
        relay_reference.all_off()

    def set_volume(self, volume: float) -> None:
        if volume < 0.0 or volume > 1.0:
            print(f'Invalid volume: {volume}, it will be ignored')
            return

        pygame.mixer.music.set_volume(volume)

    def get_volume(self) -> float:
        return pygame.mixer.music.get_volume()

    def get_info(self) -> None:
        pass


class _LightsController(_ControllerModule):
    def all_on(self) -> None:
        relay_reference.all_on()

    def all_off(self) -> None:
        relay_reference.all_off()

    def turn_on(self, light_name: str) -> None:
        relay_reference.mapping[light_name].on()

    def turn_off(self, light_name: str) -> None:
        relay_reference.mapping[light_name].off()

    def toggle(self, light_name: str) -> None:
        relay_reference.mapping[light_name].toggle()

    def get_info(self) -> None:
        pass


class _PresetController(_ControllerModule):
    CONFIG_PATH = Path('config/presets.json')

    def __init__(self):
        self.presets: dict[str, list[str]] = json.loads(self.CONFIG_PATH.read_text())

    def _save(self) -> None:
        self.CONFIG_PATH.write_text(json.dumps(self.presets))

    def activate(self, preset_name: str) -> None:
        light_names = self.presets[preset_name]

        # turn off all relays and turn on only the lights in the preset
        relay_reference.all_off()
        for light_name in light_names:
            relay_reference.mapping[light_name].on()

    def add_preset(self, preset_name: str, light_names: list[str]) -> None:
        self.presets[preset_name] = light_names
        self._save()

    def get_info(self) -> None:
        pass


class RemapAlreadyStarted(Exception):
    def __init__(self):
        super().__init__('Remap is already in progress. Use cancel_remap and try again.')


class NoRemapInProgress(Exception):
    def __init__(self):
        super().__init__('There is no remap in progress. Use start_remap and try again.')


class RemapNameDoesNotExist(Exception):
    def __init__(self, name: str):
        super().__init__(f'No light found with name: {name}')


class _RemapController(_ControllerModule):
    def __init__(self):
        self.remap: dict[str, int | None] | None = None
        self.relay_iterator: Iterator | None = None
        self.current_relay: Relay | None = None

    def start(self) -> None:
        if self.remap is not None:
            raise RemapAlreadyStarted()

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

    def next(self, assign_light_name: str) -> bool:
        if assign_light_name not in relay_reference.mapping:
            raise RemapNameDoesNotExist(assign_light_name)

        # assign pin of light name to remap
        self.remap[assign_light_name] = self.current_relay.pin.number

        # turn off current relay and turn on next
        self.current_relay.off()
        try:
            self.current_relay = next(self.relay_iterator)
            self.current_relay.on()
            return True
        except StopIteration:
            self._stop()
            return False

    def cancel(self) -> None:
        self._stop()

    def _stop(self) -> None:
        self.relay_iterator = None
        self.current_relay = None

        # save only if remap is complete
        if all(self.remap.values()):
            json_data = json.dumps(self.remap)
            relay_reference.CONFIG_PATH.write_text(json_data)
            relay_reference.reload()

        self.remap = None

    def get_info(self) -> None:
        pass


class _DeveloperController(_ControllerModule):
    def __init__(self, vixen_dir: Path):
        self.vixen_dir = vixen_dir

    def recompile_shows(self) -> None:
        print_progress('Scanning vixen_dir for all songs...')
        song_dict = VixenScanner(self.vixen_dir).scan()
        all_show_files = [generate_show_file(song) for song in song_dict.values()]
        upload_shows(all_show_files)
        print_done()

    def get_info(self) -> None:
        pass


# ------------------------------------------------------------------------------------------------


class Controller:
    def __init__(self, vixen_dir: str):
        self.vixen_dir = Path(vixen_dir)

        # add controller modules
        self.songs = _SongsController(self.vixen_dir)
        self.lights = _LightsController()
        self.presets = _PresetController()
        self.remap = _RemapController()
        self.developer = _DeveloperController(self.vixen_dir)


# ------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    c = Controller(DEBUG_VIXEN_DIR)
