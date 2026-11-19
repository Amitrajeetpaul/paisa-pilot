"""Computer vision preprocessing agent for camera photos and blurry scans.
Applies:
1. EXIF orientation correction (fixes smartphone camera rotation).
2. Auto-Contrast & Dynamic Range stretch (fixes washed out / shadowy paper).
3. Unsharp Mask sharpening (sharpens blurred characters & numbers).
"""

from __future__ import annotations

import io
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def enhance_document_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, bool]:
    """Enhances a document image if it is a JPEG or PNG.
    Returns (enhanced_bytes, was_enhanced).
    """
    if "image" not in mime_type and not mime_type.startswith("image/"):
        return image_bytes, False

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # 1. Correct EXIF orientation from smartphone cameras
            img = ImageOps.exif_transpose(img) or img

            # Convert to RGB if needed (handles RGBA / palette)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 2. Auto-contrast stretch (clips 1% outliers to remove shadows/faded ink)
            img = ImageOps.autocontrast(img, cutoff=1)

            # 3. Enhance Contrast moderately (1.25x)
            contrast = ImageEnhance.Contrast(img)
            img = contrast.enhance(1.25)

            # 4. Sharpen blurred text with unsharp mask
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

            # Export back to JPEG bytes
            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=92, optimize=True)
            return out_buf.getvalue(), True
    except Exception:
        # Graceful fallback: return original bytes if processing fails
        return image_bytes, False
