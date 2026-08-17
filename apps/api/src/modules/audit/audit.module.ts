import { Module, Global } from '@nestjs/common';
import { Injectable } from '@nestjs/common';
import { Controller, Get, Param, Query, Req, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';
import { DatabaseModule } from '../../database/database.module';

@Injectable()
export class AuditService {
  constructor(private prisma: PrismaService) {}

  async log(data: {
    schoolId: string;
    userId?: string;
    action: string;
    entity: string;
    entityId?: string;
    oldValue?: any;
    newValue?: any;
    ipAddress?: string;
    userAgent?: string;
    metadata?: any;
    severity?: string;
  }) {
    try {
      return await this.prisma.auditLog.create({ data });
    } catch (e) {
      console.error('Audit log failed:', e);
    }
  }

  async getLogs(schoolId: string, query: any = {}) {
    const { page = 1, limit = 50, entity, userId, action, severity, from, to } = query;
    const where: any = { schoolId };
    if (entity) where.entity = entity;
    if (userId) where.userId = userId;
    if (action) where.action = { contains: action, mode: 'insensitive' };
    if (severity) where.severity = severity;
    if (from || to) where.createdAt = {};
    if (from) where.createdAt.gte = new Date(from);
    if (to) where.createdAt.lte = new Date(to);

    const [data, total] = await Promise.all([
      this.prisma.auditLog.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * limit,
        take: +limit,
      }),
      this.prisma.auditLog.count({ where }),
    ]);
    return { data, total, page: +page, limit: +limit, pages: Math.ceil(total / limit) };
  }

  async getEntityHistory(schoolId: string, entity: string, entityId: string) {
    return this.prisma.auditLog.findMany({
      where: { schoolId, entity, entityId },
      orderBy: { createdAt: 'desc' },
    });
  }

  async getActivitySummary(schoolId: string) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

    const [todayCount, weekCount, byEntity, bySeverity] = await Promise.all([
      this.prisma.auditLog.count({ where: { schoolId, createdAt: { gte: today } } }),
      this.prisma.auditLog.count({ where: { schoolId, createdAt: { gte: weekAgo } } }),
      this.prisma.auditLog.groupBy({ by: ['entity'], where: { schoolId }, _count: true, orderBy: { _count: { entity: 'desc' } }, take: 10 }),
      this.prisma.auditLog.groupBy({ by: ['severity'], where: { schoolId }, _count: true }),
    ]);
    return { todayCount, weekCount, byEntity, bySeverity };
  }
}

@Controller('audit')
@UseGuards(JwtAuthGuard, PermissionsGuard)
class AuditController {
  constructor(private readonly audit: AuditService) {}

  @Get('logs') @RequirePermissions('audit:audit:READ') getLogs(@Req() r: any, @Query() q: any) { return this.audit.getLogs(r.user.schoolId, q); }
  @Get('summary') @RequirePermissions('audit:audit:READ') getSummary(@Req() r: any) { return this.audit.getActivitySummary(r.user.schoolId); }
  @Get('logs/:entity/:entityId') @RequirePermissions('audit:audit:READ') getEntityHistory(@Req() r: any, @Param('entity') entity: string, @Param('entityId') entityId: string) {
    return this.audit.getEntityHistory(r.user.schoolId, entity, entityId);
  }
}

@Global()
@Module({
  imports: [DatabaseModule],
  controllers: [AuditController],
  providers: [AuditService],
  exports: [AuditService],
})
export class AuditModule {}
