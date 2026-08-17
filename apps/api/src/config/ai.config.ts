import { registerAs } from '@nestjs/config';
export default registerAs('ai', () => ({
  openaiApiKey: process.env.OPENAI_API_KEY,
  model: process.env.AI_MODEL || 'gpt-4o-mini',
  maxTokens: parseInt(process.env.AI_MAX_TOKENS || '2000', 10),
}));
