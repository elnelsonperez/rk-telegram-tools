import { InlineKeyboard } from "grammy";

export const DOC_TYPE_LABELS: Record<string, string> = {
  COT: "cotización",
  PRES: "presupuesto",
  REC: "recibo de pago",
  CARTA: "carta de compromiso",
};

export function getDocTypeKeyboard(): InlineKeyboard {
  return new InlineKeyboard()
    .text("📄 Cotización", "new_doc:COT")
    .text("📋 Presupuesto", "new_doc:PRES")
    .row()
    .text("🧾 Recibo", "new_doc:REC")
    .text("📝 Carta", "new_doc:CARTA")
    .row()
    .text("📎 Otro documento", "new_doc:OTHER");
}

export function getConfirmKeyboard(): InlineKeyboard {
  return new InlineKeyboard()
    .text("Generar ✅", "action:generate")
    .text("✏️ Modificar", "action:modify")
    .row()
    .text("❌ Cancelar", "action:cancel");
}

export function getPostGenerateKeyboard(): InlineKeyboard {
  return new InlineKeyboard()
    .text("✏️ Editar", "action:modify")
    .text("📄 Nuevo Doc", "action:new_doc");
}

export function getResumeKeyboard(): InlineKeyboard {
  return new InlineKeyboard()
    .text("Continuar ▶️", "session:resume")
    .text("🆕 Empezar de nuevo", "session:new");
}
