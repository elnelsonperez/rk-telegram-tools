---
name: rk-artside-documents
description: Generate professional PDF documents (cotizaciones, presupuestos, recibos, cartas de compromiso) for RK ArtSide SRL. Use when user mentions documento, cotización, presupuesto, recibo, factura, carta, compromiso, or RK ArtSide.
---

# RK ArtSide Document Generator

## Overview
Generate professional PDF documents (quotations, budgets, payment receipts) for RK ArtSide SRL, an interior design company in Santiago, Dominican Republic.

## When to Use
Use this skill when the user asks to create:
- Cotización / Quotation
- Presupuesto / Budget
- Recibo de pago / Payment receipt
- Carta de compromiso / Commitment letter

Or mentions: documento, factura, cliente, precio, ITBIS, RK ArtSide, carta, compromiso

## Company Info
- **Name:** RK ArtSide SRL
- **RNC:** 1-33-51750-7
- **Email:** rkartside@gmail.com
- **Phone:** 809 645 7575
- **Contact:** Reyka Kawashiro
- **Location:** Santiago, R.D.
- **Currency:** RD$ (Dominican Pesos)

## Brand Colors
```python
GOLD = '#9A8455'       # Primary
CREAM = '#FFF6ED'      # Background
DARK = '#333333'       # Text
LIGHT_GOLD = '#C4B896' # Accents
```

## Assets
The following assets are included in this skill's `assets/` folder:
- `logo.png` - RK ArtSide logo
- `sello.png` - Company stamp

Copy these to your working directory before generating documents.

## Document Types

### 1. COTIZACIÓN (Quotation)
**Use for:** Pricing before confirming work
**Structure:**
- Header with logo + company info
- Title "COTIZACIÓN" + number (COT-YYYY-NNN) + date
- Client info
- Table: Description | Qty | Unit Price | ITBIS | Subtotal
- Section subtotals if multiple categories
- Tax breakdown + Total
- Company stamp

### 2. PRESUPUESTO (Budget)
**Use for:** Specific projects with descriptions
**Structure:**
- Header with logo + company info
- Title "PRESUPUESTO" + subtitle + number (PRES-YYYY-NNN) + date
- Client info
- Work description (table or descriptive text)
- Specifications/includes if applicable
- Total
- Company stamp

### 3. RECIBO DE PAGO (Payment Receipt)
**Use for:** Confirming received payments
**Structure:**
- Header with logo + company info
- Title "RECIBO DE PAGO" + number (REC-YYYY-NNN) + date
- "Recibido de:" + client name (use spacing=70 for proper spacing before amount box)
- Amount (highlighted in gold box)
- Payment concept
- ITBIS breakdown if applicable
- Company stamp

**Important:** When calling `draw_client()` for recibos with label "RECIBIDO DE:", use `spacing=70` parameter to add more space before the amount box.

### 4. CARTA DE COMPROMISO (Commitment Letter)
**Use for:** Formalizing project agreements with clients
**Structure:**
- Header with logo + company info
- Title "CARTA DE COMPROMISO" + number (CARTA-YYYY-NNN) + date
- Personalized salutation
- Introduction paragraphs (customizable)
- Sections with gold titles (customizable):
  - Visita y Propuesta Digital (with fee amount)
  - Plazo de Entrega (with delivery days and project description)
  - Pago y Financiamiento
  - Propiedad Intelectual
- Closing paragraphs (customizable)
- Client signature line
- Company stamp

**Flexibility:** The commitment letter supports custom content:
- Default content covers standard terms
- All paragraphs and sections can be modified if needed
- Claude can adapt text based on specific client requirements

**Required parameters:**
- `client_name`: Client's full name
- `project_description`: What will be delivered
- `visit_fee`: Amount for visit and digital proposal (RD$)
- `delivery_days`: Number of days for delivery

**Optional parameters** (for customization):
- `salutation`: Custom salutation (e.g., "Estimada Sra. Mariel Rosario:"). Infer "Estimado" or "Estimada" from the client's name.
- `intro_paragraphs`: Custom introduction text
- `sections`: Modified or additional sections
- `closing_paragraphs`: Custom closing text

## ITBIS Rules (18% Tax)
**Applies to:** Cotizaciones, Presupuestos, Recibos. **Does NOT apply to Cartas de Compromiso.**
**ALWAYS ask the user:**
1. Do prices include ITBIS or not?
2. Should the document show ITBIS breakdown?

**Calculations:**
- If prices INCLUDE ITBIS: `Subtotal = Total / 1.18`, `ITBIS = Total - Subtotal`
- If prices EXCLUDE ITBIS: `ITBIS = Subtotal * 0.18`, `Total = Subtotal + ITBIS`

## Workflow
1. Identify document type
2. Gather: client name, items/services, quantities, prices
3. **Ask about ITBIS** (included? show breakdown?)
4. **Verify math manually** before generating
5. Generate PDF using template from TEMPLATE.py
6. Present to user

## Date Format
- Default: Current date
- Format: DD/MM/YYYY
- User can specify different date

## Generation
Use the template in TEMPLATE.py. Key steps:
```python
# 1. Copy assets
# 2. Import template class
# 3. Create document instance
# 4. Add content
# 5. Save and present
```

See TEMPLATE.py for complete implementation.
