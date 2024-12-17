import json
from pathlib import Path
from typing import TypeAlias, Iterable

import gpiozero

Relay: TypeAlias = gpiozero.LED
RelayMapping: TypeAlias = dict[str, Relay]


class RelayReference:
    CONFIG_PATH = Path('config/rr_mapping.json')

    def __init__(self):
        self.mapping: RelayMapping = {}
        self.reload()

    def reload(self):
        # close all gpiozero.LED connections if they exist
        if len(self.mapping) > 0:
            for relay in self.mapping.values():
                relay.close()

        mapping_json = json.loads(self.CONFIG_PATH.read_text())
        self.mapping = {
            key: gpiozero.LED(value)
            for key, value in mapping_json.items()
        }

    @property
    def relays(self) -> Iterable[Relay]:
        return self.mapping.values()

    def all_off(self) -> None:
        for relay in self.mapping.values():
            relay.off()

    def all_on(self) -> None:
        for relay in self.mapping.values():
            relay.on()


# for some reason, this static type declaration is necessary for global singletons...
relay_reference: RelayReference = RelayReference()
