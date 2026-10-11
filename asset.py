from pathlib import Path

from PIL import Image

RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS
IMAGE_DIR = Path(__file__).resolve().parent / "image"

icon = Image.open(IMAGE_DIR / "reload_icon.png")
reload_icon = icon.resize((40, 40), RESAMPLE)

icon_2 = Image.open(IMAGE_DIR / "logout.png")
logout_icon = icon_2.resize((30, 30), RESAMPLE)

icon_3 = Image.open(IMAGE_DIR / "chatroom.png")
chatroom_icon = icon_3.resize((70, 45), RESAMPLE)

img = Image.open(IMAGE_DIR / "im.png")
request_image = img.resize((90, 55), RESAMPLE)

img_2 = Image.open(IMAGE_DIR / "im2.png")
friend_image = img_2.resize((70, 70), RESAMPLE)

img_3 = Image.open(IMAGE_DIR / "signup.jpg")
signup_image = img_3.resize((520, 480), RESAMPLE)

img_4 = Image.open(IMAGE_DIR / "login.jpg")
login_image = img_4.resize((520, 480), RESAMPLE)
