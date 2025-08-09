import badge
import time
from machine import unique_id

if 0:
    from internal_os.hardware.radio import Packet

ICON_LOCATIONS = [
    (44, 2),
    (92, 2),
    (140, 2),
]
ICON_NAMES = [
    'happy',
    'happy',
    'happy',
]
ICON_IMAGES = [badge.display.import_pbm(f'/apps/radar/assets/{name}.pbm') for name in ICON_NAMES]
ICON_COUNT = len(ICON_LOCATIONS)


class App(badge.BaseApp):
    def on_open(self) -> None:
        try:
            with open(badge.utils.get_data_dir() + "/contact_id.txt", "r") as f:
                self.contact_id = int(f.read())
        except:
            self.contact_id = None
        self.queued_emojis = []
        self.display()

    def loop(self) -> None:
        pass

    # views

    def display(self):
        if self.contact_id is None and 0:  # FIXME
            self.display_no_contact()
        else:
            self.display_messaging()
        badge.display.show()

    def display_no_contact(self):
        pass

    def display_messaging(self):
        badge.display.fill(1)
        badge.display.rect(20, 20, 160, 160, 0)
        for i in range(ICON_COUNT):
            x, y = ICON_LOCATIONS[i]
            self.draw_icon(i, x, y)

    # components

    def draw_icon(self, icon: int, x: int, y: int):
        badge.display.blit(ICON_IMAGES[icon], x, y)
