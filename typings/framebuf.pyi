from array import array
from typing import type_check_only
from typing_extensions import Buffer

@type_check_only
class _Format: ...

MONO_VLSB: _Format
MONO_HLSB: _Format
MONO_HMSB: _Format
RGB565: _Format
GS2_HMSB: _Format
GS4_HMSB: _Format
GS8: _Format

class FrameBuffer:
    def __init__(
        self,
        buffer: Buffer,
        width: int,
        height: int,
        format: _Format,
        stride: int = ...,
    ) -> None: ...
    def fill(self, c: int) -> None: ...
    def pixel(self, x: int, y: int, c: int = ...) -> None: ...
    def hline(self, x: int, y: int, w: int, c: int) -> None: ...
    def vline(self, x: int, y: int, h: int, c: int) -> None: ...
    def line(self, x1: int, y1: int, x2: int, y2: int, c: int) -> None: ...
    def rect(self, x: int, y: int, w: int, h: int, c: int, f: bool = False) -> None: ...
    def ellipse(
        self, x: int, y: int, xr: int, yr: int, c: int, f: bool = False, m: int = ...
    ) -> None: ...
    def polygon(
        self, x: int, y: int, coords: array[int], c: int, f: bool = False
    ) -> None: ...
    def text(self, s: str, x: int, y: int, c: int = 1) -> None: ...
    def blit(
        self,
        fbuf: (
            FrameBuffer
            | tuple[Buffer, int, int, _Format]
            | tuple[Buffer, int, int, _Format, int]
        ),
        x: int,
        y: int,
        key: int = ...,
        palette: FrameBuffer | None = None,
    ) -> None: ...
