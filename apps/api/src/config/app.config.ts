import { registerAs } from '@nestjs/config';

export default registerAs('app', () => ({
  port: parseInt(process.env.PORT || '3001', 10),
  env: process.env.NODE_ENV || 'development',
  frontendUrl: process.env.FRONTEND_URL || 'http://localhost:3000',
  allowedOrigins: process.env.ALLOWED_ORIGINS || 'http://localhost:3000',
  rateLimitShort: parseInt(process.env.RATE_LIMIT_SHORT || '10', 10),
  rateLimitMedium: parseInt(process.env.RATE_LIMIT_MEDIUM || '50', 10),
  rateLimitLong: parseInt(process.env.RATE_LIMIT_LONG || '100', 10),
}));
