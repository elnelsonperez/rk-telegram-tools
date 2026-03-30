import { z } from "zod";

const envSchema = z.object({
  TELEGRAM_BOT_TOKEN: z.string().min(1),
  TELEGRAM_WEBHOOK_SECRET: z.string().min(1),
  ANTHROPIC_API_KEY: z.string().min(1),
  RK_SKILL_ID: z.string().min(1),
  DATABASE_URL: z.string().min(1),
  SONIOX_API_KEY: z.string().min(1),
  NODE_ENV: z.enum(["development", "production"]).default("development"),
});

export type Config = z.infer<typeof envSchema>;

export function loadConfig(): Config {
  return envSchema.parse(process.env);
}
