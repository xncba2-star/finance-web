import re
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

def extract_receipt_text(uploaded_file):
    image = Image.open(uploaded_file).convert("RGB")
    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = image.resize((image.width * 2, image.height * 2))
    try:
        return pytesseract.image_to_string(image, lang="ind+eng")
    except Exception:
        return pytesseract.image_to_string(image, lang="eng")

def suggest_amount(text):
    candidates = []
    patterns = [
        r'(?i)(?:total|jumlah|grand\s*total|tagihan|tunai|bayar)\D{0,20}([0-9][0-9.,]{2,})',
        r'(?<!\d)([0-9]{1,3}(?:[.,][0-9]{3})+)(?!\d)'
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text or ""):
            digits = re.sub(r"\D", "", match)
            if digits:
                value = int(digits)
                if 1000 <= value <= 100_000_000:
                    candidates.append(value)
    return max(candidates) if candidates else 0
