import time

if 0:
    from internal_os.hardware.radio import Packet
    
import badge
from badge.input import Buttons
from machine import unique_id

from .image import Image

ICON_LOCATIONS = [
    (44, 1),
    (92, 1),
    (140, 1),
    (1, 35),
    (1, 73),
    (1, 111),
    (1, 149),
    (183, 35),
    (183, 73),
    (183, 111),
    (183, 149),
]

ICON_BUTTONS = [
    Buttons.SW15,
    Buttons.SW8,
    Buttons.SW16,
    Buttons.SW5,
    Buttons.SW18,
    Buttons.SW10,
    Buttons.SW17,
    Buttons.SW7,
    Buttons.SW13,
    Buttons.SW6,
    Buttons.SW14,
]

ICON_COUNT = len(ICON_LOCATIONS)

MESSAGE_LIMIT = 15


class Message:
    __slots__ = ('from_id', 'to_id', 'content')

    def __init__(self, from_id: int, to_id: int, content: list[str]):
        self.from_id = from_id
        self.to_id = to_id
        self.content = content


class App(badge.BaseApp):
    def on_open(self) -> None:
        self.messages: list[Message] = []
        try:
            with open(badge.utils.get_data_dir() + "/contact_id.txt", "r") as f:
                self.contact_id = int(f.read())
        except:
            self.contact_id = None
        self.queued_emojis: list[str] = []
        self.needs_update = True
        self.wrote_id = False

    def loop(self) -> None:
        if self.needs_update:
            self.display()
            self.needs_update = False
        if self.contact_id is None:
            self.handle_no_contact()
        else:
            self.handle_messaging()

    # logic

    def handle_no_contact(self):
        if badge.uart.is_connected():
            if not self.wrote_id:
                badge.uart.send(unique_id()[-2:])
                self.wrote_id = True

            badge_id = int.from_bytes(self.uart_read_blocking(2), 'big')
            self.contact_id = badge_id
            with open(badge.utils.get_data_dir() + "/contact_id.txt", "w") as f:
                f.write(str(self.contact_id))
            self.needs_update = True

        elif badge.uart.present():
            success = badge.uart.try_connect()
            if not success:
                raise RuntimeError("UART connection failed, probably driver error")

    def handle_messaging(self):
        assert self.contact_id is not None
        for button in ICON_BUTTONS:
            if badge.input.get_button(button):
                icon_index = ICON_BUTTONS.index(button)
                self.queued_emojis.append(ICON_NAMES[icon_index])

        if badge.input.get_button(Buttons.SW4):
            if self.queued_emojis:
                packet_data = bytearray()
                packet_data.append(0x01)  # message packet
                packet_data.append(len(self.queued_emojis))
                for emoji in self.queued_emojis:
                    emoji_index = ICON_NAMES.index(emoji)
                    packet_data.append(emoji_index)
                badge.radio.send_packet(self.contact_id, packet_data)
                self.queued_emojis.clear()

    # views

    def display(self):
        if False:
            self.display_no_contact()
        else:
            self.display_messaging()
        badge.display.show()

    def display_no_contact(self):
        badge.display.fill(1)
        # TODO change placeholder
        badge.display.fill_rect(60, 30, 80, 80, 0)
        badge.display.rect(20, 120, 65, 40, 0)
        badge.display.rect(115, 120, 65, 40, 0)
        badge.display.hline(85, 130, 10, 0)
        badge.display.hline(85, 140, 10, 0)
        badge.display.hline(85, 150, 10, 0)
        badge.display.hline(105, 130, 10, 0)
        badge.display.hline(105, 140, 10, 0)
        badge.display.hline(105, 150, 10, 0)

    def display_messaging(self):
        badge.display.fill(1)
        badge.display.rect(20, 20, 160, 160, 0)
        for i in range(ICON_COUNT):
            x, y = ICON_LOCATIONS[i]
            Image.draw_image_name("happy", x, y)

    # components
    
    # uart

    def uart_read_blocking(self, num_bytes: int, timeout: int = 5) -> bytes:
        start_time = badge.time.monotonic()
        data = b''
        while True:
            data += badge.uart.receive(num_bytes - len(data))
            if len(data) >= num_bytes:
                return data
            if badge.time.monotonic() - start_time > timeout:
                raise TimeoutError("Timeout waiting for UART data")
            time.sleep(0.01)

    # radio

    def on_packet(self, packet: Packet, in_foreground: bool) -> None:
        data = packet.data
        if packet.source != self.contact_id:
            self.logger.warning(f"Ignoring packet from unknown source {hex(packet.source)}")
            return
        if data[0] == 0x01:
            # message packet
            num_emojis = data[1]
            emojis = []
            for i in range(num_emojis):
                emoji_index = data[2 + i]
                emoji_name = ICON_NAMES[emoji_index]
                emojis.append(emoji_name)
            message = Message(packet.source, packet.dest, emojis)
            self.add_message(message)
            if in_foreground:
                self.needs_update = True

    # storage

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > MESSAGE_LIMIT:
            self.messages.pop(0)
        self._save_messages()

    def _save_messages(self) -> None:
        try:
            with open(badge.utils.get_data_dir() + "/messages.txt", "w") as f:
                for message in self.messages:
                    line = f"{message.from_id}:{message.to_id}:{','.join(message.content)}\n"
                    f.write(line)
        except Exception as e:
            print("Error saving messages:", e)
