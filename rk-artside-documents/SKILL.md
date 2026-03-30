---
name: rk-artside-documents
description: Generate professional branded PDF documents for RK ArtSide SRL using HTML and WeasyPrint. Use when the user asks to create any document — cotizaciones, presupuestos, recibos, cartas, contratos, facturas, or any professional document.
---

# RK ArtSide Document Generator

## Overview

Generate professional PDF documents using HTML + CSS + WeasyPrint for RK ArtSide SRL, an interior design company in Santiago, Dominican Republic. This is a **brand system**, not a fixed set of document types. Use the brand toolkit and component library to compose **any** document type the user needs.

## Brand System

### Colors
| Token       | Hex       | Usage                     |
|-------------|-----------|---------------------------|
| Gold        | `#9A8455` | Primary — headings, lines, accents |
| Cream       | `#FFF6ED` | Page / section backgrounds |
| Dark        | `#333333` | Body text                 |
| Light Gold  | `#C4B896` | Borders, subtle accents   |
| White       | `#FFFFFF` | Table header text, contrast |

### Typography
- **Font stack:** Helvetica, Arial, sans-serif
- **Headings:** Gold color, bold weight
- **Body:** Dark (#333) color, regular weight
- **Sizes:** Title 24px, subtitles 14px, body 10-11px, fine print 8px

### Assets
Located in this skill's `assets/` folder:
- **`logo.png`** — RK ArtSide logo. Place in the document header.
- **`sello.png`** — Company stamp. Place near signatures or at the end of the document.

Copy assets to the working directory before generating:
```bash
cp /path/to/skill/assets/logo.png /home/claude/logo.png
cp /path/to/skill/assets/sello.png /home/claude/sello.png
```

### Page Size
- **Default:** Legal (8.5in x 14in)
- Claude may choose A4, Letter, or landscape orientation if the content calls for it

## WeasyPrint Workflow

```bash
pip install weasyprint --break-system-packages
```

```python
from weasyprint import HTML
import base64, pathlib

# Convert images to data URIs for reliable embedding
def img_to_data_uri(path):
    data = pathlib.Path(path).read_bytes()
    b64 = base64.b64encode(data).decode()
    ext = pathlib.Path(path).suffix.lstrip('.')
    mime = 'image/png' if ext == 'png' else f'image/{ext}'
    return f'data:{mime};base64,{b64}'

logo_uri = img_to_data_uri('/home/claude/logo.png')
sello_uri = img_to_data_uri('/home/claude/sello.png')

# Insert data URIs into <img src="..."> tags in html_content
HTML(string=html_content).write_pdf('/home/claude/output.pdf')
```

## Company Info

| Field      | Value                  |
|------------|------------------------|
| Name       | RK ArtSide SRL         |
| RNC        | 1-33-51750-7           |
| Email      | rkartside@gmail.com    |
| Phone      | 809 645 7575           |
| Contact    | Reyka Kawashiro         |
| Location   | Santiago, R.D.         |
| Currency   | RD$ (user can override)|

## ITBIS Rules (18% Dominican Tax)

**ITBIS is OPT-IN ONLY.** Do NOT compute, ask about, or mention ITBIS unless the user explicitly brings it up.

When the user requests ITBIS:
- **Prices include ITBIS:** Subtotal = Total / 1.18, ITBIS = Total - Subtotal
- **Prices exclude ITBIS:** ITBIS = Subtotal x 0.18, Total = Subtotal + ITBIS
- Show a clear breakdown: Subtotal, ITBIS (18%), Total

## HTML/CSS Component Library

See **references/patterns.md** for the complete set of reusable HTML/CSS components including:
- Base page template with @page rules
- Branded header with logo
- Client info block
- Item tables (simple and with ITBIS)
- Totals sections
- Amount highlight box
- Signature areas
- Stamp placement
- Full example compositions

## Example Document Types

These are **examples**, not the only documents possible. Claude can create ANY document type using the brand components.

### Cotizacion (COT-YYYY-NNN)
Quotation with item table, quantities, prices, and totals.

### Presupuesto (PRES-YYYY-NNN)
Project budget with descriptions and line-item costs.

### Recibo de Pago (REC-YYYY-NNN)
Payment receipt with prominent amount box and payment concept.

### Carta de Compromiso (CARTA-YYYY-NNN)
Commitment letter with customizable sections, terms, and signature area.

## Date Format

- Default: current date
- Format: DD/MM/YYYY
- User can specify a different date

## Workflow

1. Identify what the user needs (document type, content, audience)
2. Gather: client name, items/services, quantities, prices, any special requirements
3. Generate ITBIS breakdown **only if the user mentioned it**
4. Verify all math manually before generating
5. Build HTML using components from references/patterns.md
6. Generate PDF with WeasyPrint
7. Present to user
