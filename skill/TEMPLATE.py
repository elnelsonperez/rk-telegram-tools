"""
RK ArtSide Document Generator Template
======================================
Use this template to generate professional PDFs for RK ArtSide SRL.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.enums import TA_JUSTIFY
from datetime import datetime

# Brand Colors
GOLD = HexColor('#9A8455')
CREAM = HexColor('#FFF6ED')
DARK = HexColor('#333333')
LIGHT_GOLD = HexColor('#C4B896')
WHITE = HexColor('#FFFFFF')

# Asset paths (copy from skill folder first)
LOGO_PATH = '/home/claude/logo.png'
STAMP_PATH = '/home/claude/sello.png'


class RKDocument:
    """Base class for RK ArtSide documents."""
    
    def __init__(self, filename, doc_title, doc_number, date=None, subtitle=None):
        self.c = canvas.Canvas(filename, pagesize=letter)
        self.width, self.height = letter
        self.doc_title = doc_title
        self.doc_number = doc_number
        self.date = date or datetime.now().strftime("%d/%m/%Y")
        self.subtitle = subtitle
        self.y_pos = self.height
        
    def draw_header(self):
        """Draw header with logo and company info."""
        # Cream background
        self.c.setFillColor(CREAM)
        self.c.rect(0, self.height - 120, self.width, 120, fill=True, stroke=False)
        
        # Logo
        logo = ImageReader(LOGO_PATH)
        self.c.drawImage(logo, 50, self.height - 90, width=150, height=60,
                        preserveAspectRatio=True, mask='auto')
        
        # Company info
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 8)
        self.c.drawRightString(self.width - 50, self.height - 40, "RK ArtSide SRL")
        self.c.drawRightString(self.width - 50, self.height - 50, "rkartside@gmail.com")
        self.c.drawRightString(self.width - 50, self.height - 60, "Tel: 809 645 7575")
        self.c.drawRightString(self.width - 50, self.height - 70, "Reyka Kawashiro")
        
        # Gold line
        self.c.setStrokeColor(GOLD)
        self.c.setLineWidth(2)
        self.c.line(50, self.height - 130, self.width - 50, self.height - 130)
        
        # Title
        self.c.setFillColor(GOLD)
        self.c.setFont("Helvetica-Bold", 24)
        self.c.drawString(50, self.height - 170, self.doc_title.upper())
        
        # Subtitle if provided
        if self.subtitle:
            self.c.setFont("Helvetica-Bold", 14)
            self.c.drawString(50, self.height - 195, self.subtitle)
        
        # Date and number
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 9)
        self.c.drawRightString(self.width - 50, self.height - 160, f"Fecha: {self.date}")
        self.c.drawRightString(self.width - 50, self.height - 172, f"No: {self.doc_number}")
        
        self.y_pos = self.height - 220
        
    def draw_client(self, client_name, company_name=None, label="CLIENTE:", spacing=40):
        """Draw client information.
        
        Args:
            client_name: Name of the client
            company_name: Optional company name
            label: Label text (default "CLIENTE:")
            spacing: Vertical spacing after this section in pixels (default 40)
        """
        self.c.setFillColor(GOLD)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(50, self.y_pos, label)
        
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 11)
        self.c.drawString(50 + len(label) * 6 + 10, self.y_pos, client_name)
        
        if company_name:
            self.y_pos -= 15
            self.c.setFont("Helvetica-Oblique", 10)
            self.c.drawString(50 + len(label) * 6 + 10, self.y_pos, company_name)
        
        self.y_pos -= spacing
        
    def draw_table_header_simple(self):
        """Draw simple table header (Description + Amount)."""
        self.c.setFillColor(GOLD)
        self.c.rect(50, self.y_pos - 5, self.width - 100, 25, fill=True, stroke=False)
        
        self.c.setFillColor(WHITE)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(60, self.y_pos + 3, "DESCRIPCIÓN")
        self.c.drawString(450, self.y_pos + 3, "MONTO")
        
        self.y_pos -= 30
        
    def draw_table_header_full(self):
        """Draw full table header with ITBIS columns."""
        self.c.setFillColor(GOLD)
        self.c.rect(50, self.y_pos - 5, self.width - 100, 25, fill=True, stroke=False)
        
        self.c.setFillColor(WHITE)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(60, self.y_pos + 3, "DESCRIPCIÓN")
        self.c.drawString(280, self.y_pos + 3, "CANT.")
        self.c.drawString(320, self.y_pos + 3, "P. UNIT.")
        self.c.drawString(390, self.y_pos + 3, "ITBIS")
        self.c.drawString(450, self.y_pos + 3, "SUBTOTAL")
        
        self.y_pos -= 30
        
    def draw_section_title(self, title):
        """Draw section title."""
        self.c.setFont("Helvetica-Bold", 10)
        self.c.setFillColor(GOLD)
        self.c.drawString(60, self.y_pos, title)
        self.y_pos -= 18
        
    def draw_line_item_simple(self, description, amount):
        """Draw simple line item (description + amount)."""
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 10)
        
        self.c.drawString(60, self.y_pos, description)
        self.c.drawRightString(555, self.y_pos, f"RD$ {amount:,.2f}")
        
        self.c.setStrokeColor(LIGHT_GOLD)
        self.c.setLineWidth(0.5)
        self.c.line(60, self.y_pos - 10, self.width - 60, self.y_pos - 10)
        
        self.y_pos -= 28
        
    def draw_line_item_full(self, description, qty, unit_price, include_itbis=True):
        """Draw full line item with ITBIS calculation."""
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 9)
        
        subtotal = qty * unit_price
        if include_itbis:
            # Price includes ITBIS, calculate breakdown
            precio_sin_itbis = unit_price / 1.18
            itbis_unit = unit_price - precio_sin_itbis
            itbis_line = itbis_unit * qty
        else:
            itbis_line = 0
        
        self.c.drawString(60, self.y_pos, description)
        self.c.drawString(285, self.y_pos, str(qty))
        self.c.drawRightString(370, self.y_pos, f"{unit_price:,.2f}")
        self.c.drawRightString(430, self.y_pos, f"{itbis_line:,.2f}")
        self.c.drawRightString(555, self.y_pos, f"{subtotal:,.2f}")
        
        self.c.setStrokeColor(LIGHT_GOLD)
        self.c.setLineWidth(0.5)
        self.c.line(60, self.y_pos - 6, self.width - 60, self.y_pos - 6)
        
        self.y_pos -= 18
        
        return subtotal, itbis_line
        
    def draw_section_subtotal(self, label, amount):
        """Draw section subtotal."""
        self.y_pos -= 5
        self.c.setFillColor(GOLD)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(350, self.y_pos, label)
        self.c.drawRightString(555, self.y_pos, f"RD$ {amount:,.2f}")
        self.y_pos -= 25
        
    def draw_totals_with_itbis(self, subtotal, itbis, total):
        """Draw totals section with ITBIS breakdown."""
        self.y_pos -= 10
        
        self.c.setStrokeColor(GOLD)
        self.c.setLineWidth(2)
        self.c.line(350, self.y_pos + 15, self.width - 50, self.y_pos + 15)
        
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 11)
        self.c.drawString(380, self.y_pos, "Subtotal:")
        self.c.drawRightString(555, self.y_pos, f"RD$ {subtotal:,.2f}")
        
        self.y_pos -= 20
        self.c.drawString(380, self.y_pos, "ITBIS (18%):")
        self.c.drawRightString(555, self.y_pos, f"RD$ {itbis:,.2f}")
        
        self.y_pos -= 25
        self.c.setStrokeColor(LIGHT_GOLD)
        self.c.setLineWidth(1)
        self.c.line(380, self.y_pos + 10, self.width - 50, self.y_pos + 10)
        
        self.y_pos -= 10
        self.c.setFillColor(GOLD)
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawString(380, self.y_pos, "TOTAL:")
        self.c.drawRightString(555, self.y_pos, f"RD$ {total:,.2f}")
        
    def draw_total_simple(self, total):
        """Draw simple total without ITBIS breakdown."""
        self.y_pos -= 10
        
        self.c.setStrokeColor(GOLD)
        self.c.setLineWidth(2)
        self.c.line(350, self.y_pos + 15, self.width - 50, self.y_pos + 15)
        
        self.y_pos -= 5
        self.c.setFillColor(GOLD)
        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawString(380, self.y_pos, "TOTAL:")
        self.c.drawRightString(555, self.y_pos, f"RD$ {total:,.2f}")
        
    def draw_amount_box(self, amount, label="MONTO RECIBIDO:"):
        """Draw highlighted amount box (for receipts)."""
        self.c.setFillColor(GOLD)
        self.c.roundRect(50, self.y_pos - 10, self.width - 100, 50, 5, fill=True, stroke=False)
        
        self.c.setFillColor(WHITE)
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawString(70, self.y_pos + 20, label)
        
        self.c.setFont("Helvetica-Bold", 22)
        self.c.drawRightString(self.width - 70, self.y_pos + 15, f"RD$ {amount:,.2f}")
        
        self.y_pos -= 70
        
    def draw_concept(self, concept):
        """Draw concept section (for receipts)."""
        self.c.setFillColor(GOLD)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(50, self.y_pos, "CONCEPTO:")
        
        self.y_pos -= 20
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 11)
        self.c.drawString(50, self.y_pos, concept)
        
        self.y_pos -= 40
        
    def draw_description_block(self, title, lines):
        """Draw description block with multiple lines."""
        self.c.setFillColor(GOLD)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(50, self.y_pos, title)
        
        self.y_pos -= 20
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica", 11)
        
        for line in lines:
            self.c.drawString(50, self.y_pos, line)
            self.y_pos -= 18
            
        self.y_pos -= 10
        
    def draw_stamp(self):
        """Draw company stamp at bottom."""
        stamp = ImageReader(STAMP_PATH)
        self.c.drawImage(stamp, self.width - 200, 80, width=120, height=120,
                        preserveAspectRatio=True, mask='auto')
    
    def draw_paragraph_block(self, paragraphs, y_start, y_end):
        """Draw formatted paragraphs with automatic text wrapping.
        
        Args:
            paragraphs: List of paragraph text (can include HTML markup)
            y_start: Starting Y position
            y_end: Ending Y position (bottom limit)
        
        Returns:
            Final Y position after drawing paragraphs
        """
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=DARK,
            alignment=TA_JUSTIFY,
            spaceBefore=0,
            spaceAfter=12,
        )
        
        # Create a frame for the paragraphs
        frame = Frame(50, y_end, self.width - 100, y_start - y_end, 
                      leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0)
        
        # Build story
        story = []
        for para_text in paragraphs:
            p = Paragraph(para_text, body_style)
            story.append(p)
        
        # Add to frame
        frame.addFromList(story, self.c)
        
        # Return approximate final position
        return y_end + 20
    
    def draw_carta_compromiso(
        self,
        client_name,
        project_description,
        visit_fee,
        delivery_days,
        intro_paragraphs=None,
        sections=None,
        closing_paragraphs=None,
        salutation=None
    ):
        """Generate a commitment letter.
        
        Args:
            client_name: Client's name
            project_description: Description of what will be delivered
            visit_fee: Fee for visit and digital proposal (RD$)
            delivery_days: Number of days for delivery
            intro_paragraphs: Optional list of custom intro paragraphs
            sections: Optional dict of custom sections {title: content}
            closing_paragraphs: Optional list of custom closing paragraphs
        """
        # Salutation
        self.c.setFillColor(DARK)
        self.c.setFont("Helvetica-Bold", 11)
        salutation = salutation or f"Estimado/a {client_name}:"
        self.c.drawString(50, self.y_pos, salutation)
        self.y_pos -= 30
        
        # Default intro paragraphs
        if intro_paragraphs is None:
            intro_paragraphs = [
                "En nombre de nuestro equipo de diseño de interiores, nos complace presentarle nuestra propuesta para crear un espacio único y personalizado que refleje su estilo y se ajuste a su presupuesto. En nuestro enfoque, la honestidad y la transparencia son fundamentales, por lo que queremos asegurarle que no habrá cobros ni comisiones ocultas.",
                
                "Creemos que cada proyecto debe ser una experiencia en sí misma, y nos comprometemos a crear un espacio que no solo sea funcional y estéticamente atractivo, sino que también refleje su personalidad. Nuestro objetivo es superar sus expectativas y garantizar su satisfacción.",
            ]
        
        # Default sections
        if sections is None:
            sections = {
                "Visita y Propuesta Digital": f"Entendemos que cada cliente tiene necesidades y expectativas específicas. Por lo tanto, antes de iniciar el proyecto, realizaremos una visita y crearemos una propuesta digital detallada que se ajuste a sus requerimientos y gustos. Para cubrir los costos de esta fase inicial, se cobrará una tarifa de <b>RD${visit_fee:,.2f}</b> que incluye visita, propuesta digital y presupuesto presentado.",
                
                "Plazo de Entrega": f"Una vez que la propuesta sea aprobada por su parte, nos comprometemos a comenzar el proyecto de inmediato. Un plazo máximo de <b>{delivery_days} días</b> a partir de la aprobación o depósito recibirá propuesta de: {project_description}. Una vez entregada la propuesta digital y aprobada se presenta cotización de mobiliarios y ejecución.",
                
                "Pago y Financiamiento": "Este monto no es reembolsable y corresponde a lo propuesto digitalmente. Una vez entregado el documento final, se hace el pago de la propuesta entregada.<br/><br/>La propuesta digital presentada está sujeta a un cambio sin costo. En caso de que requiera otros cambios, estos tendrán un costo adicional.",
                
                "Propiedad Intelectual": f"La información contenida en este documento es propiedad única de RK ArtSide y Reyka Kawashiro y {client_name}. Cualquier reproducción en partes o en su totalidad se prohíbe sin el permiso de RK ArtSide, Reyka Kawashiro y {client_name}.",
            }
        
        # Build all content paragraphs
        all_paragraphs = []
        
        # Add intro
        all_paragraphs.extend(intro_paragraphs)
        
        # Add sections with titles
        for title, content in sections.items():
            section_para = f"<b><font color='#9A8455'>{title}:</font></b><br/>{content}"
            all_paragraphs.append(section_para)
        
        # Draw paragraphs
        content_end_y = 160  # Leave room for closing and signature
        self.draw_paragraph_block(all_paragraphs, self.y_pos, content_end_y)
        
        # Default closing paragraphs
        if closing_paragraphs is None:
            closing_paragraphs = [
                "Agradecemos la oportunidad de trabajar con usted en este emocionante proyecto.",
                "Nuestro equipo está ansioso por transformar sus ideas en realidad.",
                "",
                "Quedamos a su entera disposición para cualquier consulta o aclaración adicional."
            ]
        
        # Draw closing
        closing_y = 140
        self.c.setFont("Helvetica", 10)
        self.c.setFillColor(DARK)
        
        for line in closing_paragraphs:
            self.c.drawString(50, closing_y, line)
            closing_y -= 14
        
        # Signature area
        sig_y = 80
        
        # Client signature line
        self.c.setStrokeColor(LIGHT_GOLD)
        self.c.setLineWidth(1)
        self.c.line(50, sig_y, 250, sig_y)
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(GOLD)
        self.c.drawString(50, sig_y - 12, "Firma del Cliente")
        self.c.setFillColor(DARK)
        self.c.drawString(50, sig_y - 24, client_name)
        
        # Draw stamp
        self.draw_stamp()
        
        self.y_pos = sig_y - 40
        
    def save(self):
        """Save the document."""
        self.c.save()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

def example_cotizacion():
    """Example: Generate a quotation."""
    doc = RKDocument(
        filename="/home/claude/cotizacion_ejemplo.pdf",
        doc_title="Cotización",
        doc_number="COT-2026-001"
    )
    
    doc.draw_header()
    doc.draw_client("Juan Pérez", "Empresa XYZ")
    doc.draw_table_header_full()
    
    # Track totals
    total = 0
    total_itbis = 0
    
    # Add items
    items = [
        ("Cojines 22x22", 4, 4145),
        ("Rellenos 22x22", 4, 800),
    ]
    
    for desc, qty, price in items:
        subtotal, itbis = doc.draw_line_item_full(desc, qty, price, include_itbis=True)
        total += subtotal
        total_itbis += itbis
    
    subtotal_sin_itbis = total - total_itbis
    doc.draw_totals_with_itbis(subtotal_sin_itbis, total_itbis, total)
    doc.draw_stamp()
    doc.save()


def example_presupuesto():
    """Example: Generate a budget."""
    doc = RKDocument(
        filename="/home/claude/presupuesto_ejemplo.pdf",
        doc_title="Presupuesto",
        doc_number="PRES-2026-001",
        subtitle="Diseño de Interiores"
    )
    
    doc.draw_header()
    doc.draw_client("María López")
    
    doc.draw_description_block("DESCRIPCIÓN:", [
        "Diseño completo de sala y comedor",
        "Incluye: mobiliario, iluminación y accesorios"
    ])
    
    doc.draw_table_header_simple()
    
    items = [
        ("Diseño de concepto", 15000),
        ("Mobiliario", 85000),
        ("Iluminación", 25000),
        ("Instalación", 10000),
    ]
    
    total = 0
    for desc, amount in items:
        doc.draw_line_item_simple(desc, amount)
        total += amount
    
    doc.draw_total_simple(total)
    doc.draw_stamp()
    doc.save()


def example_recibo():
    """Example: Generate a payment receipt."""
    doc = RKDocument(
        filename="/home/claude/recibo_ejemplo.pdf",
        doc_title="Recibo de Pago",
        doc_number="REC-2026-001"
    )
    
    doc.draw_header()
    doc.draw_client("Empresa ABC S.R.L.", label="RECIBIDO DE:", spacing=70)
    doc.draw_amount_box(150000)
    doc.draw_concept("Anticipo proyecto de remodelación oficinas")
    doc.draw_stamp()
    doc.save()


def example_carta_compromiso():
    """Example: Generate a commitment letter."""
    doc = RKDocument(
        filename="/home/claude/carta_compromiso_ejemplo.pdf",
        doc_title="Carta de Compromiso",
        doc_number="CARTA-2026-001"
    )
    
    doc.draw_header()
    doc.draw_carta_compromiso(
        client_name="Sra. Mariel Rosario",
        project_description="Cocina apt.1 y cocina apt.2, Closet habitación principal Casa diseño y distribución",
        visit_fee=18500,
        delivery_days=10
    )
    doc.save()


if __name__ == "__main__":
    # Run examples
    example_cotizacion()
    example_presupuesto()
    example_recibo()
    example_carta_compromiso()
    print("Ejemplos generados exitosamente!")
