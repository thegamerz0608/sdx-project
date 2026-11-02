"""
Utility script to generate professional demo profile avatars.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

AVATAR_DIR = Path(__file__).resolve().parent.parent / "uploads" / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

AVATARS = [
    {
        "filename": "admin.png",
        "bg_color": (30, 58, 138),  # Deep Royal Blue
        "initials": "SA",
        "role_badge": "ADMIN",
        "badge_color": (37, 99, 235),
    },
    {
        "filename": "hod_mca.png",
        "bg_color": (109, 40, 217),  # Royal Purple
        "initials": "SK",
        "role_badge": "HOD",
        "badge_color": (139, 92, 246),
    },
    {
        "filename": "fac_rahul.png",
        "bg_color": (4, 120, 87),  # Emerald Green
        "initials": "RS",
        "role_badge": "FACULTY",
        "badge_color": (16, 185, 129),
    },
    {
        "filename": "inst_kavita.png",
        "bg_color": (180, 83, 9),  # Amber / Bronze
        "initials": "KN",
        "role_badge": "LAB INST",
        "badge_color": (245, 158, 11),
    },
]

def generate_avatars():
    size = (256, 256)
    for item in AVATARS:
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw circle background
        draw.ellipse([4, 4, 251, 251], fill=item["bg_color"], outline=(255, 255, 255, 200), width=6)

        # Load font
        try:
            font_initials = ImageFont.truetype("segoeui.ttf", 96)
            font_badge = ImageFont.truetype("segoeuib.ttf", 22)
        except IOError:
            try:
                font_initials = ImageFont.truetype("arial.ttf", 96)
                font_badge = ImageFont.truetype("arial.ttf", 22)
            except IOError:
                font_initials = ImageFont.load_default()
                font_badge = ImageFont.load_default()

        # Draw initials
        bbox = draw.textbbox((0, 0), item["initials"], font=font_initials)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (256 - w) / 2
        y = (240 - h) / 2 - 14
        draw.text((x, y), item["initials"], fill=(255, 255, 255), font=font_initials)

        # Draw role badge pill at bottom
        pill_w = 120
        pill_h = 32
        pill_x0 = (256 - pill_w) / 2
        pill_y0 = 196
        pill_x1 = pill_x0 + pill_w
        pill_y1 = pill_y0 + pill_h
        draw.rounded_rectangle([pill_x0, pill_y0, pill_x1, pill_y1], radius=16, fill=item["badge_color"])

        b_box = draw.textbbox((0, 0), item["role_badge"], font=font_badge)
        bw = b_box[2] - b_box[0]
        bh = b_box[3] - b_box[1]
        bx = (256 - bw) / 2
        by = pill_y0 + (pill_h - bh) / 2 - 2
        draw.text((bx, by), item["role_badge"], fill=(255, 255, 255), font=font_badge)

        out_path = AVATAR_DIR / item["filename"]
        img.save(out_path, format="PNG")
        print(f"Generated avatar: {out_path}")

if __name__ == "__main__":
    generate_avatars()
