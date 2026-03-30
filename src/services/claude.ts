import Anthropic from "@anthropic-ai/sdk";
import { SessionAction } from "../bot/session.js";
import { createLogger } from "../logger.js";

const log = createLogger("claude");
const BETAS = ["code-execution-2025-08-25", "skills-2025-10-02"];
const MAX_CONTINUATIONS = 10;

// ---------------------------------------------------------------------------
// Respond tool schema
// ---------------------------------------------------------------------------

export const RESPOND_TOOL = {
  name: "respond",
  description:
    "Use this tool to send your response to the user. Always use this tool instead of plain text.",
  input_schema: {
    type: "object" as const,
    properties: {
      text: {
        type: "string",
        description: "The message text to show the user (Telegram Markdown).",
      },
      session_action: {
        type: "string",
        enum: ["continue", "confirm", "generate", "new"],
        description:
          "continue = normal conversation, confirm = ask user to confirm before generating, generate = generate document now, new = start fresh session.",
      },
      doc_type: {
        type: "string",
        description: "Document type identifier when generating (e.g. 'invoice', 'receipt').",
      },
      doc_data: {
        type: "object",
        properties: {
          title: { type: "string" },
          clientName: { type: "string" },
        },
        description: "Document metadata when generating.",
      },
      pending_question: {
        type: "string",
        description: "A follow-up question to ask the user after document generation.",
      },
    },
    required: ["text", "session_action"],
  },
} as const;

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface ClaudeResponse {
  text: string;
  sessionAction: SessionAction;
  fileIds: string[];
  containerId: string | null;
  docType?: string;
  docData?: Record<string, unknown>;
  pendingQuestion?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function needsContinuation(stopReason: string | null | undefined): boolean {
  return stopReason === "pause_turn";
}

// biome-ignore lint/suspicious/noExplicitAny: Claude API content blocks vary in shape
export function extractResponse(content: any[]): ClaudeResponse {
  const fileIds: string[] = [];
  let respondData: ClaudeResponse | null = null;
  let lastText = "";

  for (const block of content) {
    // Collect file IDs from code execution results
    if (block.type === "bash_code_execution_tool_result") {
      const inner = block.content?.content;
      if (Array.isArray(inner)) {
        for (const item of inner) {
          if (item.file_id) {
            fileIds.push(item.file_id);
          }
        }
      }
    }

    // Extract structured data from respond tool calls
    if (block.type === "tool_use" && block.name === "respond") {
      const input = block.input as Record<string, unknown>;
      respondData = {
        text: (input.text as string) ?? "",
        sessionAction: (input.session_action as SessionAction) ?? SessionAction.Continue,
        fileIds,
        containerId: null,
        docType: input.doc_type as string | undefined,
        docData: input.doc_data as Record<string, unknown> | undefined,
        pendingQuestion: input.pending_question as string | undefined,
      };
    }

    // Track last text block as fallback
    if (block.type === "text" && typeof block.text === "string") {
      lastText = block.text;
    }
  }

  if (respondData) {
    return respondData;
  }

  // Fallback: use the last text block
  return {
    text: lastText,
    sessionAction: SessionAction.Continue,
    fileIds,
    containerId: null,
  };
}

// ---------------------------------------------------------------------------
// System prompt
// ---------------------------------------------------------------------------

const SYSTEM_PROMPT = `Eres un asistente de generación de documentos para RK ArtSide, una empresa de servicios creativos en República Dominicana.

REGLAS IMPORTANTES:
1. SIEMPRE usa la herramienta "respond" para enviar tus respuestas. Nunca respondas con texto plano.
2. ITBIS: Solo incluye ITBIS si el usuario lo menciona explícitamente. No preguntes sobre ITBIS a menos que el usuario lo traiga a colación.
3. Cuando session_action sea "generate", DEBES usar code_execution en el mismo turno para generar el documento.
4. Formato de texto: Usa formato Markdown compatible con Telegram:
   - *negrita* para énfasis
   - _cursiva_ para notas
   - \`código\` para valores
   - No uses encabezados (#)
   - NUNCA uses tablas Markdown (no se renderizan en Telegram). Usa listas con - o • en su lugar.
   - Listas con - o • están bien.
5. Moneda: Por defecto usa RD$ (pesos dominicanos), pero si el usuario indica otra moneda (USD, EUR, etc.), úsala sin cuestionar.
6. Sé conciso y profesional. Responde en español.
7. Para documentos, recopila la información necesaria paso a paso antes de generar.`;

// ---------------------------------------------------------------------------
// Claude client
// ---------------------------------------------------------------------------

export class ClaudeClient {
  private client: Anthropic;

  constructor(apiKey: string) {
    this.client = new Anthropic({ apiKey });
  }

  async sendMessage(
    messages: Anthropic.MessageParam[],
    skillId: string,
    systemExtra?: string,
    containerId?: string,
  ): Promise<ClaudeResponse> {
    // Split system into stable (cacheable) and dynamic (per-turn) blocks
    const system: Array<{ type: "text"; text: string; cache_control?: { type: "ephemeral" } }> = [
      { type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } },
    ];
    if (systemExtra) {
      system.push({ type: "text", text: systemExtra });
    }

    const container: Record<string, unknown> = {
      skills: [{ type: "custom", skill_id: skillId, version: "latest" }],
    };
    if (containerId) {
      container.id = containerId;
    }

    const tools = [
      { type: "code_execution_20250825" as const, name: "code_execution" as const },
      { ...RESPOND_TOOL, cache_control: { type: "ephemeral" as const } },
    ];

    log.info({ messageCount: messages.length, skillId, containerId }, "Sending Claude API request");

    // biome-ignore lint/suspicious/noExplicitAny: Anthropic SDK types for beta APIs
    let response: any = await (this.client.beta.messages as any).create({
      model: "claude-sonnet-4-6",
      max_tokens: 16384,
      betas: BETAS,
      system,
      container,
      messages,
      tools,
    });

    // Handle pause_turn continuations.
    // Accumulate content blocks from ALL responses so we don't miss
    // the respond tool call if it happens in an intermediate turn.
    const allContent: unknown[] = [...(response.content as unknown[])];
    let currentMessages = [...messages];
    let continuations = 0;

    for (let i = 0; i < MAX_CONTINUATIONS; i++) {
      if (!needsContinuation(response.stop_reason)) break;
      continuations++;
      log.info(
        { continuation: continuations, stopReason: response.stop_reason },
        "pause_turn continuation",
      );

      currentMessages = [...currentMessages, { role: "assistant", content: response.content }];

      // biome-ignore lint/suspicious/noExplicitAny: Anthropic SDK types for beta APIs
      response = await (this.client.beta.messages as any).create({
        model: "claude-sonnet-4-6",
        max_tokens: 16384,
        betas: BETAS,
        system,
        container: { id: response.container?.id, ...container },
        messages: currentMessages,
        tools,
      });
      allContent.push(...(response.content as unknown[]));
    }

    const result = extractResponse(allContent);
    result.containerId = response.container?.id ?? null;
    // biome-ignore lint/suspicious/noExplicitAny: usage type from beta API
    const usage = response.usage as any;
    log.info(
      {
        action: result.sessionAction,
        fileCount: result.fileIds.length,
        continuations,
        containerId: result.containerId,
        inputTokens: usage?.input_tokens,
        outputTokens: usage?.output_tokens,
        cacheRead: usage?.cache_read_input_tokens,
        cacheCreation: usage?.cache_creation_input_tokens,
      },
      "Claude response complete",
    );
    return result;
  }

  async downloadFile(fileId: string): Promise<Buffer> {
    // biome-ignore lint/suspicious/noExplicitAny: beta files API
    const fileResponse = await (this.client.beta as any).files.download(fileId, {
      betas: ["files-api-2025-04-14"],
    });

    const chunks: Uint8Array[] = [];
    const reader = fileResponse.body.getReader();

    let streamDone = false;
    while (!streamDone) {
      const { done, value } = await reader.read();
      streamDone = done;
      if (!done) {
        chunks.push(value);
      }
    }

    return Buffer.concat(chunks);
  }
}
