import badge
import time
from machine import unique_id

if 0:
    from internal_os.hardware.radio import Packet


class App(badge.BaseApp):
    def on_open(self) -> None:
        self.present = False
        self.connected = False
        self.connect_failed = None
        self.hash = -1
        self._ping_mono = 0
        self.ping = None
        self._is_pinging = False
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
        if badge.input.get_button(badge.input.Buttons.SW5):
            if not self._is_pinging:
                self._is_pinging = True
                if self.partner is not None:
                    self._ping_mono = badge.time.monotonic()
                    badge.radio.send_packet(self.partner, b'\x03')
        else:
            self._is_pinging = False
        if self.hash != self._get_hash():
            self.hash = self._get_hash()
            self._display()
        if self.connected:
            self._handle_uart()

    def on_packet(self, packet: 'Packet', in_foreground: bool) -> None:
        opcode = packet.data[0]
        if opcode == 0x03:
            badge.radio.send_packet(packet.source, b'\x04')
        elif opcode == 0x04:
            self.ping = badge.time.monotonic() - self._ping_mono

    def _handle_uart(self):
        opcode = badge.uart.receive(1)
        if opcode:
            if opcode[0] == 0x01:
                badge.uart.send(b"\x02" + unique_id()[-2:])
            elif opcode[0] == 0x02:
                data = self._blocking_read(2)
                self._set_partner(int.from_bytes(data, 'big'))

    def _display(self):
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
            badge.display.nice_text(f"Partner {hex(self.partner)}", 0, 60)
        else:
            badge.display.nice_text("No Partner", 0, 60)
        if self.ping is not None:
            badge.display.nice_text(f"Ping {self.ping*1000:.1f}ms", 0, 80)
        badge.display.show()

    def _blocking_read(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = badge.uart.receive(size - len(data))
            if chunk:
                data.extend(chunk)
            else:
                time.sleep(0.1)
        return bytes(data)

    def _set_partner(self, partner_id: int):
        self.partner = partner_id
        try:
            with open(badge.utils.get_data_dir() + '/partner.txt', 'w') as f:
                f.write(str(partner_id))
        except Exception as e:
            self.logger.error(f"Failed to write partner ID: {e}")

    def _get_hash(self):
        return hash(
            (self.present, self.connected, self.connect_failed, self.partner, self.ping)
        )
