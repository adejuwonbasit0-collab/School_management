import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';
import { INestApplication } from '@nestjs/common';

const PrismaClientBase: any = PrismaClient;

@Injectable()
export class PrismaService extends PrismaClientBase implements OnModuleInit, OnModuleDestroy {
  [key: string]: any;

  constructor() {
    super({
      log: process.env.NODE_ENV === 'development'
        ? ['query', 'info', 'warn', 'error']
        : ['error'],
      errorFormat: 'colorless',
    });
  }

  async onModuleInit() {
    await this.$connect();
    this.setupMiddleware();
  }

  async onModuleDestroy() {
    await this.$disconnect();
  }

  async enableShutdownHooks(app: INestApplication) {
    process.on('beforeExit', async () => {
      await app.close();
    });
  }

  private setupMiddleware() {
    // Soft delete middleware
    this.$use(async (params, next) => {
      // Query performance logging in dev
      if (process.env.NODE_ENV === 'development') {
        const before = Date.now();
        const result = await next(params);
        const after = Date.now();
        if (after - before > 100) {
          console.warn(`Slow query (${after - before}ms): ${params.model}.${params.action}`);
        }
        return result;
      }
      return next(params);
    });
  }

  async cleanDatabase() {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('Cannot clean database in production');
    }
    const tablenames = await this.$queryRaw<Array<{ tablename: string }>>`
      SELECT tablename FROM pg_tables WHERE schemaname='public'
    `;
    for (const { tablename } of tablenames) {
      if (tablename !== '_prisma_migrations') {
        try {
          await this.$executeRawUnsafe(`TRUNCATE TABLE "public"."${tablename}" CASCADE;`);
        } catch (error) {
          console.log({ error });
        }
      }
    }
  }
}
