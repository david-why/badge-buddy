import badge

class Image:
    __IMAGE_CODES = (
        0x01,
        0x02,
        0x03
    )
    __IMAGE_NAMES = (
        'emojis/happy',
        'emojis/happy',
        'emojis/happy'
    )
    
    __IMAGES_BY_NAME = {
        name.lower(): badge.display.import_pbm(f'/apps/radar/assets/{name}.pbm') for name in __IMAGE_NAMES
    }
    
    __CODE_TO_NAME = {
        code: name.lower() for code, name in zip(__IMAGE_CODES, __IMAGE_NAMES)
    }
    
    @classmethod
    def draw_image_code(cls, code: int, x: int, y: int) -> None:
        name = cls.__CODE_TO_NAME.get(code)
        if name is None:
            raise ValueError(f"Invalid image code: {code}")
        framebuffer = cls.__IMAGES_BY_NAME[name]
        badge.display.blit(framebuffer, x, y)
    
    @classmethod
    def draw_image_name(cls, name: str, x: int, y: int) -> None:
        framebuffer = cls.__IMAGES_BY_NAME.get(name.lower())
        if framebuffer is None:
            raise ValueError(f"Invalid image name: {name}")
        badge.display.blit(framebuffer, x, y)
