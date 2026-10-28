import csv
import os
import uuid

import qrcode
from PIL import Image, ImageDraw, ImageFont

os.makedirs('cards', exist_ok=True)

children = []
for i in range(1, 51):
    children.append({
        'uuid': str(uuid.uuid4()),
        'name': f'Child {i:02d}'
    })

with open('children.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['uuid', 'name'])
    writer.writeheader()
    writer.writerows(children)

for child in children:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(child['uuid'])
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    card = Image.new('RGB', (700, 450), 'white')
    card.paste(img, (50, 50))
    draw = ImageDraw.Draw(card)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font = ImageFont.load_default()

    draw.text((50, 340), child['name'], fill='black', font=font)
    draw.text((50, 390), f"ID: {child['uuid'][:8]}", fill='gray', font=font)
    card.save(f"cards/{child['uuid'][:8]}.png")

print(f"Done. {len(children)} cards generated in ./cards/")
print("children.csv written. Keep it — it is needed for deployment.")