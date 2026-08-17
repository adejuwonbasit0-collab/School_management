import { registerAs } from '@nestjs/config';
export default registerAs('jwt', () => ({
  accessSecret: process.env.JWT_ACCESS_SECRET || 'educore-access-secret-change-in-production',
  refreshSecret: process.env.JWT_REFRESH_SECRET || 'educore-refresh-secret-change-in-production',
  accessExpiresIn: process.env.JWT_ACCESS_EXPIRES_IN || '15m',
  refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d',
}));
