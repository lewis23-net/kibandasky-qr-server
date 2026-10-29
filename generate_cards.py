import csv
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

os.makedirs('cards', exist_ok=True)

def load_font(size, bold=False):
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibrib.ttf" if bold else "C:\\Windows\\Fonts\\calibri.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def make_qr_image(uuid_str):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,  
        border=6,     
    )
    # This exact URL opens your Render app and routes perfectly
    qr.add_data(f"https://kibandasky-qr-server.onrender.com/scan/{uuid_str}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    if hasattr(img, "get_image"):
        img = img.get_image()
    return img.convert("RGB")

# Generate PREDICTABLE UUIDs so the database and the cards ALWAYS match
children = []
for i in range(1, 51):
    short = f"{i:03d}"
    # e.g., 00000000-0000-0000-0000-000000000001
    uid = f"00000000-0000-0000-0000-{i:012d}"
    children.append({
        "uuid": uid,
        "name": f"Child {i:02d}",
        "short_id": short,
    })

with open("children.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["uuid", "name", "short_id"])
    writer.writeheader()
    writer.writerows(children)

with open("cards.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["short_id", "name", "uuid"])
    writer.writeheader()
    for c in children:
        writer.writerow({"short_id": c["short_id"], "name": c["name"], "uuid": c["uuid"]})

for child in children:
    qr_img = make_qr_image(child["uuid"])
    qr_width, qr_height = qr_img.size

    front_width = max(qr_width + 80, 800)
    front_height = qr_height + 150
    
    front = Image.new("RGB", (front_width, front_height), "white")
    qr_x = (front_width - qr_width) // 2
    front.paste(qr_img, (qr_x, 40)) 
    
    draw = ImageDraw.Draw(front)
    name_font = load_font(40, bold=True)
    small_font = load_font(24)
    
    draw.text((front_width // 2, front_height - 70), child["name"], fill="black", font=name_font, anchor="mm")
    draw.text((front_width // 2, front_height - 25), "Kibanda Meal Program", fill="gray", font=small_font, anchor="mm")

    back_width = 800
    back_height = 600
    back = Image.new("RGB", (back_width, back_height), "white")
    draw = ImageDraw.Draw(back)
    big_font = load_font(200, bold=True)
    header_font = load_font(40, bold=True)
    label_font = load_font(32)

    draw.rectangle([20, 20, back_width - 20, back_height - 20], outline="black", width=6)
    draw.text((back_width // 2, 100), "CARD ID", fill="black", font=header_font, anchor="mm")
    draw.text((back_width // 2, 280), child["short_id"], fill="black", font=big_font, anchor="mm")
    draw.line([(120, 380), (back_width - 120, 380)], fill="black", width=4)
    draw.text((back_width // 2, 440), child["name"], fill="black", font=label_font, anchor="mm")
    draw.text((back_width // 2, 520), "If found, return to Kibanda Meal Program", fill="gray", font=load_font(20), anchor="mm")

    front.save(f"cards/{child['short_id']}_{child['name'].replace(' ', '')}_front.png")
    back.save(f"cards/{child['short_id']}_{child['name'].replace(' ', '')}_back.png")

print(f"Done. {len(children)} unique cards generated in ./cards/")