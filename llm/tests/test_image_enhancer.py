import io
from PIL import Image
from llm.image_enhancer import enhance_document_image


def test_enhance_document_image_valid_jpeg():
    # Create a small test RGB image
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    original_bytes = buf.getvalue()

    enhanced, was_enhanced = enhance_document_image(original_bytes, "image/jpeg")
    assert was_enhanced is True
    assert len(enhanced) > 0
    # Verify the output is a valid JPEG
    with Image.open(io.BytesIO(enhanced)) as out_img:
        assert out_img.format == "JPEG"
        assert out_img.size == (100, 100)


def test_enhance_document_image_non_image():
    pdf_bytes = b"%PDF-1.4 mock pdf data"
    out_bytes, was_enhanced = enhance_document_image(pdf_bytes, "application/pdf")
    assert was_enhanced is False
    assert out_bytes == pdf_bytes


def test_enhance_document_image_corrupt_data():
    corrupt_bytes = b"not an actual image"
    out_bytes, was_enhanced = enhance_document_image(corrupt_bytes, "image/jpeg")
    assert was_enhanced is False
    assert out_bytes == corrupt_bytes
