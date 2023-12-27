import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def create_book_spine(title, author, doi):
    # Generate QR code for DOI
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(doi)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Create PDF with specific dimensions
    c = canvas.Canvas("book_spine.pdf", pagesize=(1.5 * cm, 21 * cm))
    c.setFont("Helvetica", 12)

    # Add title and author
    c.drawString(0.2 * cm, 19 * cm, title)
    c.drawString(0.2 * cm, 18 * cm, author)

    # Add QR code for DOI at the bottom
    qr_img_path = "doi_qr.png"
    qr_img.save(qr_img_path)
    c.drawImage(qr_img_path, 0.2 * cm, 0.5 * cm, 1.1 * cm, 1.1 * cm)

    c.save()

import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def create_book_spine(title, author, doi):
    # Generate QR code for DOI
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr.add_data(doi)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Create PDF with specific dimensions
    c = canvas.Canvas("book_spine.pdf", pagesize=(1.5 * cm, 20 * cm))

    # Rotate the canvas to write vertical text
    c.rotate(90)

    # Set font to Helvetica-Bold for title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, -0.8 * cm, title)

    # Set font back to Helvetica for author
    c.setFont("Helvetica", 12)
    c.drawString(3 * cm, -1.3 * cm, author)

    # Reset rotation for the QR code
    c.rotate(-90)

    # Add QR code for DOI at the bottom
    qr_img_path = "doi_qr.png"
    qr_img.save(qr_img_path)
    c.drawImage(qr_img_path, 0.2 * cm, 0.5 * cm, 1.1 * cm, 1.1 * cm, mask='auto')

    c.save()

create_book_spine(
    "Books title",
    "Author",
    "URL"
)
