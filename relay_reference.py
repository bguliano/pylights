import json
from pathlib import Path

import gpiozero


class RelayReference:
    RR_RELAYS_CONFIG_PATH = Path('config/rr_relays.json')
    RR_MAPPING_CONFIG_PATH = Path('config/rr_mapping.json')

    def __init__(self):
        self.relays: list[gpiozero.LED] = []
        self.mapping: dict[str, int] = {}
        self.reload()

    def reload(self):
        relays_json = json.loads(self.RR_RELAYS_CONFIG_PATH.read_text())
        mapping_json = json.loads(self.RR_MAPPING_CONFIG_PATH.read_text())

        self.relays = [gpiozero.LED(pin) for pin in relays_json]
        self.mapping = mapping_json

    def get_relay_from_name(self, name: str) -> gpiozero.LED:
        return self.relays[self.mapping[name]]


relay_reference = RelayReference()
