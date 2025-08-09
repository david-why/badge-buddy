import badge
import time
from machine import unique_id


class App(badge.BaseApp):
    def on_open(self) -> None:
        self.present = False
        self.connected = False
        self.connect_failed = None
        self.hash = -1
        try:
            with open(badge.utils.get_data_dir() + '/partner.txt', 'r') as f:
                self.partner = int(f.read().strip())
        except Exception as e:
            self.logger.error(f"Failed to read partner ID: {e}")
            self.partner = None

    def loop(self) -> None:
        self.present = badge.uart.present()
        self.connected = self.present and badge.uart.is_connected()
        if self.present and not self.connected and self.connect_failed is None:
            self.connect_failed = not badge.uart.try_connect()
            if not self.connect_failed:
                badge.uart.send(b'\x01')
        if badge.input.get_button(badge.input.Buttons.SW4):
            self.connect_failed = None
        if self.hash != self._get_hash():
            self.hash = self._get_hash()
            badge.display.fill(1)
            if self.present:
                badge.display.nice_text("Present", 0, 0)
            else:
                badge.display.nice_text("Not Present", 0, 0)
            if self.connected:
                badge.display.nice_text("Connected", 0, 20)
            else:
                badge.display.nice_text("Not Connected", 0, 20)
            if self.connect_failed is not None:
                badge.display.nice_text(f"Failed: {self.connect_failed}", 0, 40)
            if self.partner is not None:
                badge.display.nice_text(f"Partner 0x{hex(self.partner)}", 0, 60)
            else:
                badge.display.nice_text("No Partner", 0, 60)
            badge.display.show()
        if self.connected:
            self._handle_uart()
            
    def _handle_uart(self):
        opcode = badge.uart.receive(1)
        if opcode:
            if opcode[0] == 0x01:
                badge.uart.send(b"\x02" + unique_id()[-2:])
            elif opcode[0] == 0x02:
                data = self._blocking_read(2)
                self.partner = int.from_bytes(data, 'big')

    def _blocking_read(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = badge.uart.receive(size - len(data))
            if chunk:
                data.extend(chunk)
            else:
                time.sleep(0.1)
        return bytes(data)

    def _get_hash(self):
        return hash((self.present, self.connected, self.connect_failed, self.partner))
