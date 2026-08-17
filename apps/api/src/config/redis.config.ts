import { registerAs } from '@nestjs/config';

const redisPassword = process.env.REDIS_PASSWORD?.trim();

export default registerAs('redis', () => ({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379', 10),
  password: redisPassword ? redisPassword : undefined,
}));
