from abc import ABC, abstractmethod
from pathlib import Path

import mutagen.mp3
import pygame

from common import Song, Light, Preset
from relay_reference import relay_reference
from show_file_generator import generate_show_file
from vixen_scanner import VixenScanner
from zero_manager import upload_shows


class _ControllerModule(ABC):
    @abstractmethod
    def get_info(self) -> None:
        pass


# ------------------------------------------------------------------------------------------------


class _SongsController(_ControllerModule):
    def __init__(self, songs_dict: dict[str, Song]):
        self.songs = songs_dict

        pygame.mixer.init()

    def play(self, song_name: str) -> None:
        # get Song object
        song = self.songs[song_name]

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

    def resume(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass

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
    def __init__(self, lights_dict: dict[str, Light]):
        self.lights = lights_dict

    def all_on(self) -> None:
        for relay in relay_reference.relays:
            relay.on()

    def all_off(self) -> None:
        for relay in relay_reference.relays:
            relay.off()

    def turn_on(self, light_name: str) -> None:
        relay_reference.get_relay_from_name(light_name).on()

    def turn_off(self, light_name: str) -> None:
        relay_reference.get_relay_from_name(light_name).off()

    def toggle(self, light_name: str) -> None:
        relay_reference.get_relay_from_name(light_name).toggle()

    def get_info(self) -> None:
        pass


class _PresetController(_ControllerModule):
    def __init__(self, presets_dict: dict[str, Preset]):
        self.presets = presets_dict

    def activate(self, preset_name: str) -> None:
        # grab actual Preset object
        preset = self.presets[preset_name]

        # turn off all relays and turn on only the lights in the preset
        for relay in relay_reference.relays:
            relay.off()
        for light_name in preset.light_names:
            relay_reference.get_relay_from_name(light_name).on()

    def get_info(self) -> None:
        pass


class _SetupController(_ControllerModule):
    def __init__(self):
        pass

    def start_remap(self) -> None:
        pass

    def next_remap(self) -> None:
        pass

    def end_remap(self) -> None:
        pass

    def cancel_remap(self) -> None:
        pass

    def get_info(self) -> None:
        pass


class _DeveloperController(_ControllerModule):
    def __init__(self, vixen_dir: Path):
        self.vixen_dir = vixen_dir

    def recompile_shows(self) -> None:
        print('Scanning vixen_dir for all songs...', end='', flush=True)
        all_songs = VixenScanner(self.vixen_dir).scan()
        all_show_files = [generate_show_file(song) for song in all_songs]
        upload_shows(all_show_files)

    def get_info(self) -> None:
        pass


# ------------------------------------------------------------------------------------------------

class _Player(Thread):
    def __init__(self, controller: Controller):
        Thread.__init__(self)
        self.controller = controller
        pygame.mixer.init()
        self.volume = 20

        self.song: Optional[Song] = None

    def play(self, song: Song):
        old_volume = self.volume
        pygame.mixer.quit()
        freq = mutagen.mp3.MP3(song.mp3_filepath).info.sample_rate
        pygame.mixer.init(frequency=freq)
        self.volume = old_volume
        pygame.mixer.music.load(song.mp3_filepath)
        pygame.mixer.music.play()
        self.song = song

    def pause(self):
        pygame.mixer.music.pause()

    def resume(self):
        pygame.mixer.music.unpause()

    def stop(self):
        self.song = None
        pygame.mixer.music.stop()

    @property
    def volume(self) -> int:
        return int(pygame.mixer.music.get_volume() * 100)

    @volume.setter
    def volume(self, value: int):
        value = min(max(value, 0), 100)
        pygame.mixer.music.set_volume(value / 100)

    def run(self) -> None:
        while True:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy() and self.song is not None:
                data = self.song.fseq_parser.bytes_at_ms(max(0, pygame.mixer.music.get_pos() - 150))
                self.controller.bytes_to_outputs(data)


# ------------------------------------------------------------------------------------------------


class Controller:
    def __init__(self, vixen_dir: str):
        self.vixen_dir = Path(vixen_dir)
        self.songs = VixenScanner(self.vixen_dir).scan()
