from badge.input import Button

class ImageButton:
    def __init__(self, button_code: Button, image_code: int, x: int , y: int) -> None:
        self.button_code: Button = button_code
        self.image_code: int = image_code
        self.x: int = x
        self.y: int = y