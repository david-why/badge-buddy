import time

import badge
from badge.input import Buttons
from badge.radio import Packet
from machine import unique_id

from .image import Image
from .image_button import ImageButton

IMAGE_BUTTONS = [
    ImageButton(Buttons.SW15, 1, 44, 1),
    ImageButton(Buttons.SW8, 2, 92, 1),
    ImageButton(Buttons.SW16, 3, 140, 1),
    ImageButton(Buttons.SW9, 4, 1, 35),
    ImageButton(Buttons.SW18, 5, 1, 73),
    ImageButton(Buttons.SW10, 6, 1, 111),
    ImageButton(Buttons.SW17, 7, 1, 149),
    ImageButton(Buttons.SW7, 8, 183, 35),
    ImageButton(Buttons.SW13, 9, 183, 73),
    ImageButton(Buttons.SW6, 10, 183, 111),
    ImageButton(Buttons.SW14, 11, 183, 149),
]

ICON_COUNT = len(IMAGE_BUTTONS)

BADGE_ID = int.from_bytes(unique_id()[-2:], "big")
MESSAGE_COUNT_LIMIT = 15
MESSAGE_EMOJI_LIMIT = 8


class Message:
    __slots__ = ("from_id", "to_id", "content")

    def __init__(self, from_id: int, to_id: int, content: list[int]):
        self.from_id = from_id
        self.to_id = to_id
        self.content = content


class App(badge.BaseApp):
    def on_open(self) -> None:
        self.init()

    def init(self) -> None:
        self.messages: list[Message] = []
        try:
            with open(badge.utils.get_data_dir() + "/contact_id.txt", "r") as f:
                self.contact_id = int(f.read())
        except:
            self.contact_id = None
        self.queued_emojis: list[int] = []
        self.message_update_time: float | None = None
        self.keys_down: set[int] = set()
        self.needs_update = True
        self.wrote_id = False
        self._load_messages()
        self.error_msg_shown = False

    def loop(self) -> None:
        if self.error_msg_shown:
            return
        
        try:
            if self.needs_update:
                self.display()
                self.needs_update = False
            if self.contact_id is None:
                self.handle_no_contact()
            else:
                self.handle_messaging()
        except Exception as e:
            self.show_error_msg(e)

    # logic

    def handle_no_contact(self):
        if badge.uart.is_connected() and badge.uart.present():
            if not self.wrote_id:
                time.sleep(0.5)
                badge.uart.send(unique_id()[-2:])
                self.wrote_id = True

            badge_id = int.from_bytes(self.uart_read_blocking(2), "big")
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
        should_play_sound = False
        for button in IMAGE_BUTTONS:
            if badge.input.get_button(button.button_code):
                if button.button_code in self.keys_down:
                    continue
                self.keys_down.add(button.button_code)
                if len(self.queued_emojis) < MESSAGE_EMOJI_LIMIT:
                    self.queued_emojis.append(button.image_code)
                    self.message_update_time = badge.time.monotonic()
                    should_play_sound = True
            else:
                self.keys_down.discard(button.button_code)
        if should_play_sound:
            badge.buzzer.tone(440, 0.05)

        # send message
        if badge.input.get_button(Buttons.SW5):
            if self.queued_emojis:
                packet_data = bytes([0x01, len(self.queued_emojis)])
                for emoji_code in self.queued_emojis:
                    packet_data += bytes([emoji_code])
                badge.radio.send_packet(self.contact_id, packet_data)
                message = Message(BADGE_ID, self.contact_id, self.queued_emojis.copy())
                self.add_message(message)
                self.queued_emojis.clear()
                self.needs_update = True
                badge.buzzer.tone(440, 0.05)

        # backspace
        if badge.input.get_button(Buttons.SW11):
            if Buttons.SW11 not in self.keys_down:
                self.keys_down.add(Buttons.SW11)
                if self.queued_emojis:
                    self.queued_emojis.pop()
                    self.message_update_time = badge.time.monotonic()
                    badge.buzzer.tone(440, 0.05)
        else:
            self.keys_down.discard(Buttons.SW11)

        # unpair
        if badge.input.get_button(Buttons.SW12):
            badge.radio.send_packet(self.contact_id, b'\x02')
            self.unpair()

        if self.message_update_time is not None:
            if badge.time.monotonic() - self.message_update_time > 1:
                self.needs_update = True

    # views

    def display(self):
        if self.contact_id is None:
            self.display_no_contact()
        else:
            self.display_messaging()
        badge.display.show()

    def display_no_contact(self):
        badge.display.fill(1)
        Image.draw_image_code(0xFF, 0, 0)

    def display_messaging(self):
        self.message_update_time = None
        badge.display.fill(1)
        badge.display.rect(20, 20, 160, 160, 0)
        for button in IMAGE_BUTTONS:
            x, y = button.x, button.y
            Image.draw_image_code(button.image_code, x, y)
        Image.draw_image_code(0xFE, 1, 182)  # home
        Image.draw_image_code(0xFB, 46, 182)  # unpair
        # Image.draw_image_code(0x01, 92, 182)  # empty
        Image.draw_image_code(0xFC, 138, 182)  # backspace
        Image.draw_image_code(0xFD, 183, 182)  # send

        # display messages
        y_offset = 160
        if self.queued_emojis:
            self.draw_message(self.queued_emojis, "center", y_offset)
            y_offset -= 54
        for message in reversed(self.messages):
            self.logger.debug(
                f"Drawing message from {message.from_id} with content {message.content} at {y_offset}"
            )
            self.draw_message(
                message.content,
                "right" if message.from_id == BADGE_ID else "left",
                y_offset,
            )
            y_offset -= 18
            if y_offset < 22:
                break
            
    def show_error_msg(self, e: Exception) -> None:
        self.error_msg_shown = True
        
        CHARS_PER_LINE = 25
        LINE_HEIGHT = 8
        
        badge.display.fill(1)
        
        msg = str(e)
        lines = (
            [
                "Unexpected error occured:",
                ""
            ] +
            [msg[i:i+CHARS_PER_LINE] for i in range(0, len(msg), CHARS_PER_LINE)] +
            [
                "",
                "Restart the app and",
                "report this to the devs!",
                "",
                "@jollyroger182",
                "@Brooklyn Baylis"
            ]
        )

        for i, line in enumerate(lines):
            badge.display.text(line, 0, i * LINE_HEIGHT)
        
        badge.display.show()

    # components

    def draw_message(self, emojis: list[int], alignment: str, y_offset: int) -> None:
        if not emojis:
            return
        width = 18 * len(emojis) - 2
        x = (
            24
            if alignment == "left"
            else 176 - width if alignment == "right" else 100 - width // 2
        )

        for i, emoji_code in enumerate(emojis):
            x_offset = x + i * 18
            Image.draw_image_code(emoji_code, x_offset, y_offset)

    # uart

    def uart_read_blocking(self, num_bytes: int, timeout: int = 5) -> bytes:
        start_time = badge.time.monotonic()
        data = b""
        while True:
            data += badge.uart.receive(num_bytes - len(data))
            if len(data) >= num_bytes:
                return data
            if badge.time.monotonic() - start_time > timeout:
                raise RuntimeError("Timeout waiting for UART data")
            time.sleep(0.01)

    # radio

    def on_packet(self, packet: Packet, in_foreground: bool) -> None:
        data = packet.data
        if not in_foreground:
            self.init()
        if packet.source != self.contact_id:
            self.logger.warning(
                f"Ignoring packet from unknown source {hex(packet.source)}"
            )
            return
        if data[0] == 0x01:
            # message packet
            num_emojis = data[1]
            emojis = []
            for i in range(num_emojis):
                emoji_index = data[2 + i]
                emojis.append(emoji_index)
            message = Message(packet.source, packet.dest, emojis)
            self.add_message(message)
            badge.buzzer.tone(880, 0.1)
            time.sleep(0.05)
            badge.buzzer.tone(880, 0.1)
            time.sleep(0.05)
            badge.buzzer.tone(880, 0.1)
            if in_foreground:
                self.needs_update = True
        elif data[0] == 0x02:
            # unpair packet
            self.logger.info(f"Received unpair request from {hex(packet.source)}")
            self.unpair()

    # storage
    
    def unpair(self) -> None:
        self.contact_id = None
        self.messages.clear()
        self._save_messages()
        self.queued_emojis.clear()
        self.message_update_time = None
        with open(badge.utils.get_data_dir() + "/contact_id.txt", "w") as f:
            f.write("")
        self.needs_update = True

    def _load_messages(self) -> None:
        try:
            with open(badge.utils.get_data_dir() + "/messages.txt", "r") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) != 3:
                        continue
                    from_id = int(parts[0])
                    to_id = int(parts[1])
                    content = parts[2].split(",")
                    message = Message(from_id, to_id, [int(x) for x in content])
                    self.messages.append(message)
        except:
            pass

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > MESSAGE_COUNT_LIMIT:
            self.messages.pop(0)
        self._save_messages()
        self.logger.info(
            f"Added message from {message.from_id} to {message.to_id} with content {message.content}"
        )
        self.needs_update = True

    def _save_messages(self) -> None:
        try:
            with open(badge.utils.get_data_dir() + "/messages.txt", "w") as f:
                for message in self.messages:
                    line = f"{message.from_id}:{message.to_id}:{",".join(map(str, message.content))}\n"
                    f.write(line)
        except Exception as e:
            print("Error saving messages:", e)
