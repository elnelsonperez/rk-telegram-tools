# RK ArtSide — HTML/CSS Component Library

Reusable patterns for generating branded PDF documents with WeasyPrint.
Compose these components to build any document type.

---

## 1. Base Template

The full HTML skeleton. Every document starts here.

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  /* ── Page rules ── */
  @page {
    size: 8.5in 14in;          /* Legal */
    margin: 0.6in 0.7in 0.9in 0.7in;

    @bottom-center {
      content: "RK ArtSide SRL · rkartside@gmail.com · 809 645 7575";
      font-family: Helvetica, Arial, sans-serif;
      font-size: 7pt;
      color: #9A8455;
    }
  }

  @page :first {
    margin-top: 0;             /* header bleeds to top on page 1 */
  }

  /* ── Reset ── */
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #333333;
    line-height: 1.4;
  }

  /* ── Brand tokens ── */
  :root {
    --gold:       #9A8455;
    --cream:      #FFF6ED;
    --dark:       #333333;
    --light-gold: #C4B896;
    --white:      #FFFFFF;
  }

  /* ── Page-break helpers ── */
  .no-break   { page-break-inside: avoid; }
  .break-before { page-break-before: always; }
  .break-after  { page-break-after: always; }

  p { orphans: 3; widows: 3; }

  /* ── Table defaults ── */
  table {
    width: 100%;
    border-collapse: collapse;
  }
  thead { display: table-header-group; }
  tr    { page-break-inside: avoid; }

  /* === COMPONENT STYLES === */

  /* ── Header ── */
  .header {
    background: var(--cream);
    padding: 20px 0 15px 0;
    margin-bottom: 0;
  }
  .header-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header-logo img {
    height: 55px;
    width: auto;
  }
  .header-info {
    text-align: right;
    font-size: 8pt;
    color: var(--dark);
    line-height: 1.5;
  }
  .header-line {
    border: none;
    border-top: 2px solid var(--gold);
    margin: 12px 0 20px 0;
  }

  /* ── Title area ── */
  .doc-title-area {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 20px;
  }
  .doc-title {
    font-size: 24pt;
    font-weight: bold;
    color: var(--gold);
    text-transform: uppercase;
    margin: 0;
  }
  .doc-subtitle {
    font-size: 14pt;
    font-weight: bold;
    color: var(--gold);
    margin-top: 2px;
  }
  .doc-meta {
    text-align: right;
    font-size: 9pt;
    color: var(--dark);
    line-height: 1.6;
  }

  /* ── Client info ── */
  .client-info {
    margin-bottom: 25px;
  }
  .client-label {
    font-weight: bold;
    color: var(--gold);
    font-size: 10pt;
    margin-right: 8px;
  }
  .client-name {
    font-size: 11pt;
    color: var(--dark);
  }
  .client-company {
    font-style: italic;
    font-size: 10pt;
    color: var(--dark);
    margin-left: 2px;
  }

  /* ── Item table ── */
  .item-table {
    margin-bottom: 20px;
  }
  .item-table thead th {
    background: var(--gold);
    color: var(--white);
    font-size: 9pt;
    font-weight: bold;
    padding: 6px 10px;
    text-align: left;
  }
  .item-table thead th.num {
    text-align: right;
  }
  .item-table tbody td {
    padding: 6px 10px;
    font-size: 9pt;
    border-bottom: 0.5px solid var(--light-gold);
  }
  .item-table tbody td.num {
    text-align: right;
    white-space: nowrap;
  }

  /* ── Section title inside table ── */
  .section-title-row td {
    font-weight: bold;
    color: var(--gold);
    font-size: 10pt;
    padding-top: 12px;
    border-bottom: none;
  }

  /* ── Totals ── */
  .totals {
    width: 50%;
    margin-left: auto;
    margin-top: 10px;
    page-break-inside: avoid;
  }
  .totals td {
    padding: 4px 10px;
    font-size: 11pt;
  }
  .totals .label {
    text-align: left;
    color: var(--dark);
  }
  .totals .value {
    text-align: right;
    color: var(--dark);
    white-space: nowrap;
  }
  .totals .total-row td {
    border-top: 2px solid var(--gold);
    font-size: 14pt;
    font-weight: bold;
    color: var(--gold);
    padding-top: 8px;
  }
  .totals .subtotal-row td {
    border-top: 1px solid var(--light-gold);
  }

  /* ── Amount box (receipts) ── */
  .amount-box {
    background: var(--gold);
    color: var(--white);
    border-radius: 5px;
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 25px 0;
    page-break-inside: avoid;
  }
  .amount-box .amount-label {
    font-weight: bold;
    font-size: 12pt;
  }
  .amount-box .amount-value {
    font-weight: bold;
    font-size: 22pt;
  }

  /* ── Concept block ── */
  .concept-block {
    margin-bottom: 30px;
  }
  .concept-label {
    font-weight: bold;
    color: var(--gold);
    font-size: 10pt;
    margin-bottom: 6px;
  }
  .concept-text {
    font-size: 11pt;
    color: var(--dark);
  }

  /* ── Description block ── */
  .description-block {
    margin-bottom: 20px;
  }
  .description-block h3 {
    font-weight: bold;
    color: var(--gold);
    font-size: 10pt;
    margin-bottom: 6px;
  }
  .description-block p {
    font-size: 11pt;
    color: var(--dark);
    margin-bottom: 4px;
  }

  /* ── Letter body ── */
  .letter-body p {
    text-align: justify;
    font-size: 10pt;
    line-height: 1.5;
    margin-bottom: 12px;
  }
  .letter-body .section-heading {
    color: var(--gold);
    font-weight: bold;
  }

  /* ── Signature area ── */
  .signature-area {
    margin-top: 40px;
    page-break-inside: avoid;
    position: relative;
  }
  .signature-line {
    border-top: 1px solid var(--light-gold);
    width: 200px;
    margin-bottom: 4px;
  }
  .signature-label {
    font-size: 8pt;
    color: var(--gold);
  }
  .signature-name {
    font-size: 8pt;
    color: var(--dark);
  }

  /* ── Stamp ── */
  .stamp {
    page-break-inside: avoid;
  }
  .stamp img {
    width: 120px;
    height: auto;
  }
  .stamp.small img {
    width: 80px;
  }

  /* ── Stamp + signature combined layout ── */
  .sig-stamp-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 40px;
    page-break-inside: avoid;
  }

</style>
</head>
<body>
  <!-- Compose components here -->
</body>
</html>
```

---

## 2. Branded Header Component

Place at the very top of `<body>`. The logo and sello images must use data URIs (see SKILL.md workflow).

```html
<div class="header">
  <div class="header-inner">
    <div class="header-logo">
      <img src="{{LOGO_DATA_URI}}" alt="RK ArtSide">
    </div>
    <div class="header-info">
      RK ArtSide SRL<br>
      rkartside@gmail.com<br>
      Tel: 809 645 7575<br>
      Reyka Kawashiro
    </div>
  </div>
</div>
<hr class="header-line">
```

---

## 3. Title Area Component

```html
<div class="doc-title-area">
  <div>
    <h1 class="doc-title">COTIZACIÓN</h1>
    <!-- Optional subtitle: -->
    <!-- <div class="doc-subtitle">Diseño de Interiores</div> -->
  </div>
  <div class="doc-meta">
    Fecha: 15/03/2026<br>
    No: COT-2026-001
  </div>
</div>
```

---

## 4. Client Info Component

```html
<div class="client-info">
  <span class="client-label">CLIENTE:</span>
  <span class="client-name">Juan Pérez</span>
  <br>
  <!-- Optional company: -->
  <span class="client-company" style="margin-left: 60px;">Empresa XYZ</span>
</div>
```

For receipts, change the label:
```html
<div class="client-info">
  <span class="client-label">RECIBIDO DE:</span>
  <span class="client-name">Empresa ABC S.R.L.</span>
</div>
```

---

## 5. Item Table — Simple (Description + Amount)

```html
<table class="item-table">
  <thead>
    <tr>
      <th>DESCRIPCIÓN</th>
      <th class="num">MONTO</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Diseño de concepto</td>
      <td class="num">RD$ 15,000.00</td>
    </tr>
    <tr>
      <td>Mobiliario</td>
      <td class="num">RD$ 85,000.00</td>
    </tr>
  </tbody>
</table>
```

---

## 6. Item Table — Full (with Qty, Unit Price, optional ITBIS)

### Without ITBIS columns

```html
<table class="item-table">
  <thead>
    <tr>
      <th>DESCRIPCIÓN</th>
      <th class="num">CANT.</th>
      <th class="num">P. UNIT.</th>
      <th class="num">SUBTOTAL</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Cojines 22x22</td>
      <td class="num">4</td>
      <td class="num">RD$ 4,145.00</td>
      <td class="num">RD$ 16,580.00</td>
    </tr>
  </tbody>
</table>
```

### With ITBIS columns

```html
<table class="item-table">
  <thead>
    <tr>
      <th>DESCRIPCIÓN</th>
      <th class="num">CANT.</th>
      <th class="num">P. UNIT.</th>
      <th class="num">ITBIS</th>
      <th class="num">SUBTOTAL</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Cojines 22x22</td>
      <td class="num">4</td>
      <td class="num">4,145.00</td>
      <td class="num">2,521.02</td>
      <td class="num">16,580.00</td>
    </tr>
  </tbody>
</table>
```

---

## 7. Section Title Row (within a table)

Use to group items by category within the same table.

```html
<tr class="section-title-row">
  <td colspan="4">Sala Principal</td>
</tr>
```

---

## 8. Totals Section

### Simple total (no ITBIS)

```html
<table class="totals">
  <tr class="total-row">
    <td class="label">TOTAL:</td>
    <td class="value">RD$ 135,000.00</td>
  </tr>
</table>
```

### With ITBIS breakdown

```html
<table class="totals">
  <tr class="subtotal-row">
    <td class="label">Subtotal:</td>
    <td class="value">RD$ 114,406.78</td>
  </tr>
  <tr>
    <td class="label">ITBIS (18%):</td>
    <td class="value">RD$ 20,593.22</td>
  </tr>
  <tr class="total-row">
    <td class="label">TOTAL:</td>
    <td class="value">RD$ 135,000.00</td>
  </tr>
</table>
```

---

## 9. Amount Box (for Receipts)

```html
<div class="amount-box">
  <span class="amount-label">MONTO RECIBIDO:</span>
  <span class="amount-value">RD$ 150,000.00</span>
</div>
```

---

## 10. Concept Block (for Receipts)

```html
<div class="concept-block">
  <div class="concept-label">CONCEPTO:</div>
  <div class="concept-text">Anticipo proyecto de remodelación oficinas</div>
</div>
```

---

## 11. Description Block

```html
<div class="description-block">
  <h3>DESCRIPCIÓN:</h3>
  <p>Diseño completo de sala y comedor</p>
  <p>Incluye: mobiliario, iluminación y accesorios</p>
</div>
```

---

## 12. Letter Body (for Cartas)

```html
<div class="letter-body">
  <p><strong>Estimada Sra. Mariel Rosario:</strong></p>

  <p>En nombre de nuestro equipo de diseño de interiores, nos complace
  presentarle nuestra propuesta para crear un espacio único y personalizado
  que refleje su estilo y se ajuste a su presupuesto.</p>

  <p><span class="section-heading">Visita y Propuesta Digital:</span><br>
  Entendemos que cada cliente tiene necesidades y expectativas específicas.
  Para cubrir los costos de esta fase inicial, se cobrará una tarifa de
  <strong>RD$ 18,500.00</strong> que incluye visita, propuesta digital y
  presupuesto presentado.</p>

  <p><span class="section-heading">Plazo de Entrega:</span><br>
  Un plazo máximo de <strong>10 días</strong> a partir de la aprobación o
  depósito recibirá propuesta de: <strong>Cocina apt.1 y cocina apt.2,
  Closet habitación principal.</strong></p>

  <p><span class="section-heading">Pago y Financiamiento:</span><br>
  Para dar inicio al proceso de diseño, se requiere un avance del 50% del
  monto total y la firma de este documento. El 50% restante se abonará
  contra entrega. Este pago corresponde exclusivamente a la propuesta digital
  de diseño y distribución y <strong>no es reembolsable</strong>.</p>

  <p><span class="section-heading">Propiedad Intelectual:</span><br>
  La información contenida en este documento es propiedad única de RK ArtSide
  y Reyka Kawashiro y Sra. Mariel Rosario.</p>

  <p>Agradecemos la oportunidad de trabajar con usted en este emocionante
  proyecto.</p>
</div>
```

---

## 13. Signature Area

```html
<div class="signature-area">
  <div class="signature-line"></div>
  <div class="signature-label">Firma del Cliente</div>
  <div class="signature-name">Sra. Mariel Rosario</div>
</div>
```

---

## 14. Stamp

```html
<div class="stamp">
  <img src="{{SELLO_DATA_URI}}" alt="Sello RK ArtSide">
</div>
```

For commitment letters, use the smaller variant:
```html
<div class="stamp small">
  <img src="{{SELLO_DATA_URI}}" alt="Sello RK ArtSide">
</div>
```

---

## 15. Signature + Stamp Combined Layout

Common pattern: signature on the left, stamp on the right.

```html
<div class="sig-stamp-row">
  <div class="signature-area" style="margin-top: 0;">
    <div class="signature-line"></div>
    <div class="signature-label">Firma del Cliente</div>
    <div class="signature-name">Sra. Mariel Rosario</div>
  </div>
  <div class="stamp small">
    <img src="{{SELLO_DATA_URI}}" alt="Sello RK ArtSide">
  </div>
</div>
```

---

## Full Example Compositions

### A. Cotizacion (Quotation)

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  /* ... full base styles from section 1 ... */
</style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="header-inner">
      <div class="header-logo"><img src="{{LOGO_DATA_URI}}" alt="RK ArtSide"></div>
      <div class="header-info">RK ArtSide SRL<br>rkartside@gmail.com<br>Tel: 809 645 7575<br>Reyka Kawashiro</div>
    </div>
  </div>
  <hr class="header-line">

  <!-- Title -->
  <div class="doc-title-area">
    <h1 class="doc-title">Cotización</h1>
    <div class="doc-meta">Fecha: 15/03/2026<br>No: COT-2026-001</div>
  </div>

  <!-- Client -->
  <div class="client-info">
    <span class="client-label">CLIENTE:</span>
    <span class="client-name">Juan Pérez</span><br>
    <span class="client-company" style="margin-left: 60px;">Empresa XYZ</span>
  </div>

  <!-- Items -->
  <table class="item-table">
    <thead>
      <tr>
        <th>DESCRIPCIÓN</th>
        <th class="num">CANT.</th>
        <th class="num">P. UNIT.</th>
        <th class="num">SUBTOTAL</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Cojines 22x22</td><td class="num">4</td><td class="num">RD$ 4,145.00</td><td class="num">RD$ 16,580.00</td></tr>
      <tr><td>Rellenos 22x22</td><td class="num">4</td><td class="num">RD$ 800.00</td><td class="num">RD$ 3,200.00</td></tr>
    </tbody>
  </table>

  <!-- Total -->
  <table class="totals">
    <tr class="total-row">
      <td class="label">TOTAL:</td>
      <td class="value">RD$ 19,780.00</td>
    </tr>
  </table>

  <!-- Stamp -->
  <div class="stamp" style="text-align: right; margin-top: 40px;">
    <img src="{{SELLO_DATA_URI}}" alt="Sello">
  </div>

</body>
</html>
```

### B. Presupuesto (Budget)

```html
<!-- After header and title (PRESUPUESTO, with subtitle "Diseño de Interiores") -->

<div class="client-info">
  <span class="client-label">CLIENTE:</span>
  <span class="client-name">María López</span>
</div>

<div class="description-block">
  <h3>DESCRIPCIÓN:</h3>
  <p>Diseño completo de sala y comedor</p>
  <p>Incluye: mobiliario, iluminación y accesorios</p>
</div>

<table class="item-table">
  <thead>
    <tr><th>DESCRIPCIÓN</th><th class="num">MONTO</th></tr>
  </thead>
  <tbody>
    <tr><td>Diseño de concepto</td><td class="num">RD$ 15,000.00</td></tr>
    <tr><td>Mobiliario</td><td class="num">RD$ 85,000.00</td></tr>
    <tr><td>Iluminación</td><td class="num">RD$ 25,000.00</td></tr>
    <tr><td>Instalación</td><td class="num">RD$ 10,000.00</td></tr>
  </tbody>
</table>

<table class="totals">
  <tr class="total-row">
    <td class="label">TOTAL:</td>
    <td class="value">RD$ 135,000.00</td>
  </tr>
</table>

<div class="stamp" style="text-align: right; margin-top: 40px;">
  <img src="{{SELLO_DATA_URI}}" alt="Sello">
</div>
```

### C. Recibo de Pago (Payment Receipt)

```html
<!-- After header and title (RECIBO DE PAGO) -->

<div class="client-info">
  <span class="client-label">RECIBIDO DE:</span>
  <span class="client-name">Empresa ABC S.R.L.</span>
</div>

<div class="amount-box">
  <span class="amount-label">MONTO RECIBIDO:</span>
  <span class="amount-value">RD$ 150,000.00</span>
</div>

<div class="concept-block">
  <div class="concept-label">CONCEPTO:</div>
  <div class="concept-text">Anticipo proyecto de remodelación oficinas</div>
</div>

<div class="stamp" style="text-align: right; margin-top: 40px;">
  <img src="{{SELLO_DATA_URI}}" alt="Sello">
</div>
```

### D. Carta de Compromiso (Commitment Letter)

```html
<!-- After header and title (CARTA DE COMPROMISO) -->

<div class="letter-body">
  <p><strong>Estimada Sra. Mariel Rosario:</strong></p>

  <p>En nombre de nuestro equipo de diseño de interiores, nos complace
  presentarle nuestra propuesta para crear un espacio único y personalizado
  que refleje su estilo y se ajuste a su presupuesto. En nuestro enfoque,
  la honestidad y la transparencia son fundamentales, por lo que queremos
  asegurarle que no habrá cobros ni comisiones ocultas.</p>

  <p>Creemos que cada proyecto debe ser una experiencia en sí misma, y nos
  comprometemos a crear un espacio que no solo sea funcional y estéticamente
  atractivo, sino que también refleje su personalidad.</p>

  <p><span class="section-heading">Visita y Propuesta Digital:</span><br>
  Entendemos que cada cliente tiene necesidades y expectativas específicas.
  Por lo tanto, antes de iniciar el proyecto, realizaremos una visita y
  crearemos una propuesta digital detallada. Para cubrir los costos de esta
  fase inicial, se cobrará una tarifa de <strong>RD$ 18,500.00</strong> que
  incluye visita, propuesta digital y presupuesto presentado.</p>

  <p><span class="section-heading">Plazo de Entrega:</span><br>
  Un plazo máximo de <strong>10 días</strong> a partir de la aprobación o
  depósito recibirá propuesta de: <strong>Cocina apt.1 y cocina apt.2,
  Closet habitación principal Casa diseño y distribución</strong>. Una vez
  entregada la propuesta digital y aprobada se presenta cotización de
  mobiliarios y ejecución.</p>

  <p><span class="section-heading">Pago y Financiamiento:</span><br>
  Para dar inicio al proceso de diseño, se requiere un avance del 50% del
  monto total y la firma de este documento. El 50% restante se abonará
  contra entrega, al momento de presentar el documento final. Este pago
  corresponde exclusivamente a la propuesta digital de diseño y distribución
  y <strong>no es reembolsable</strong>.</p>

  <p>La cotización para la ejecución del proyecto, así como el acompañamiento
  en obra, se presentará por separado una vez aprobada la propuesta.</p>

  <p>La propuesta digital presentada está sujeta a un cambio sin costo. En
  caso de que requiera otros cambios, estos tendrán un costo adicional.</p>

  <p><span class="section-heading">Propiedad Intelectual:</span><br>
  La información contenida en este documento es propiedad única de RK ArtSide
  y Reyka Kawashiro y Sra. Mariel Rosario. Cualquier reproducción en partes o
  en su totalidad se prohíbe sin el permiso de RK ArtSide, Reyka Kawashiro y
  Sra. Mariel Rosario.</p>

  <p>Agradecemos la oportunidad de trabajar con usted en este emocionante
  proyecto. Nuestro equipo está ansioso por transformar sus ideas en
  realidad.</p>

  <p>Quedamos a su entera disposición para cualquier consulta o aclaración
  adicional.</p>
</div>

<!-- Signature + Stamp -->
<div class="sig-stamp-row">
  <div class="signature-area" style="margin-top: 0;">
    <div class="signature-line"></div>
    <div class="signature-label">Firma del Cliente</div>
    <div class="signature-name">Sra. Mariel Rosario</div>
  </div>
  <div class="stamp small">
    <img src="{{SELLO_DATA_URI}}" alt="Sello">
  </div>
</div>
```

---

## Python Helper: Build and Generate

```python
import base64, pathlib
from weasyprint import HTML

def img_to_data_uri(path):
    """Convert an image file to a base64 data URI."""
    data = pathlib.Path(path).read_bytes()
    b64 = base64.b64encode(data).decode()
    ext = pathlib.Path(path).suffix.lstrip('.')
    mime = 'image/png' if ext == 'png' else f'image/{ext}'
    return f'data:{mime};base64,{b64}'

def generate_pdf(html_content, output_path, logo_path='/home/claude/logo.png', sello_path='/home/claude/sello.png'):
    """Replace placeholders and generate PDF."""
    logo_uri = img_to_data_uri(logo_path)
    sello_uri = img_to_data_uri(sello_path)
    html_content = html_content.replace('{{LOGO_DATA_URI}}', logo_uri)
    html_content = html_content.replace('{{SELLO_DATA_URI}}', sello_uri)
    HTML(string=html_content).write_pdf(output_path)
    return output_path
```

Usage:
```python
html = """<!DOCTYPE html>..."""  # Compose from components above
generate_pdf(html, '/home/claude/cotizacion.pdf')
```
