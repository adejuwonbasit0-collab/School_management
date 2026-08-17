import { Module } from '@nestjs/common';
import { Injectable } from '@nestjs/common';
import { Controller, Get, Post, Body, Param, Req, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';
import { DatabaseModule } from '../../database/database.module';

@Injectable()
class BackupService {
  constructor(private prisma: PrismaService) {}

  async getBackups(schoolId: string) {
    return this.prisma.backupRecord.findMany({ where: { schoolId }, orderBy: { startedAt: 'desc' }, take: 50 });
  }

  async triggerBackup(schoolId: string, userId: string, type: 'FULL' | 'INCREMENTAL' = 'FULL') {
    const record = await this.prisma.backupRecord.create({
      data: { schoolId, type, status: 'RUNNING', triggeredBy: userId },
    });

    // Simulate backup process (in production, this would kick off a real backup job)
    setTimeout(async () => {
      try {
        const sizeEstimate = BigInt(Math.floor(Math.random() * 500 + 50)) * BigInt(1024 * 1024);
        await this.prisma.backupRecord.update({
          where: { id: record.id },
          data: { status: 'COMPLETED', completedAt: new Date(), size: sizeEstimate, location: `backups/${schoolId}/${record.id}.tar.gz` },
        });
      } catch (e) {
        await this.prisma.backupRecord.update({ where: { id: record.id }, data: { status: 'FAILED' } });
      }
    }, 3000);

    return record;
  }

  async getBackupStats(schoolId: string) {
    const [total, completed, failed, lastBackup] = await Promise.all([
      this.prisma.backupRecord.count({ where: { schoolId } }),
      this.prisma.backupRecord.count({ where: { schoolId, status: 'COMPLETED' } }),
      this.prisma.backupRecord.count({ where: { schoolId, status: 'FAILED' } }),
      this.prisma.backupRecord.findFirst({ where: { schoolId, status: 'COMPLETED' }, orderBy: { completedAt: 'desc' } }),
    ]);
    return { total, completed, failed, lastBackup };
  }
}

@Controller('backup')
@UseGuards(JwtAuthGuard, PermissionsGuard)
class BackupController {
  constructor(private readonly svc: BackupService) {}

  @Get('stats') @RequirePermissions('backup:backup:READ') stats(@Req() r: any) { return this.svc.getBackupStats(r.user.schoolId); }
  @Get() @RequirePermissions('backup:backup:READ') list(@Req() r: any) { return this.svc.getBackups(r.user.schoolId); }
  @Post('trigger') @RequirePermissions('backup:backup:CREATE')
  trigger(@Req() r: any, @Body() b: { type?: 'FULL' | 'INCREMENTAL' }) {
    return this.svc.triggerBackup(r.user.schoolId, r.user.id, b.type || 'FULL');
  }
}

@Module({
  imports: [DatabaseModule],
  controllers: [BackupController],
  providers: [BackupService],
  exports: [BackupService],
})
export class BackupModule {}
