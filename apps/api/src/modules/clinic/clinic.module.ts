import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Body, Param, Query, Req, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';
import { DatabaseModule } from '../../database/database.module';

@Injectable()
class ClinicService {
  constructor(private prisma: PrismaService) {}

  async getMedicalRecord(studentId?: string, staffId?: string) {
    const where = studentId ? { studentId } : { staffId };
    return this.prisma.medicalRecord.findFirst({
      where,
      include: { visits: { orderBy: { visitDate: 'desc' } } },
    });
  }

  async upsertMedicalRecord(dto: { schoolId: string; studentId?: string; staffId?: string; bloodGroup?: string; genotype?: string; allergies?: string[]; conditions?: string[]; medications?: string[]; notes?: string }) {
    const where = dto.studentId ? { studentId: dto.studentId } : { staffId: dto.staffId };
    return this.prisma.medicalRecord.upsert({
      where: dto.studentId ? { studentId: dto.studentId } : { staffId: dto.staffId },
      create: dto,
      update: dto,
      include: { visits: true },
    });
  }

  async getVisits(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20 } = query;
    const [data, total] = await Promise.all([
      this.prisma.clinicVisit.findMany({
        where: { schoolId },
        skip: (page - 1) * limit,
        take: limit,
        orderBy: { visitDate: 'desc' },
        include: { record: { select: { studentId: true, staffId: true } } },
      }),
      this.prisma.clinicVisit.count({ where: { schoolId } }),
    ]);
    return { data, total, page: +page, pages: Math.ceil(total / limit) };
  }

  async createVisit(schoolId: string, attendedBy: string, dto: { medicalRecordId: string; complaint: string; diagnosis?: string; treatment?: string; prescription?: string; referral?: string; followUpDate?: string }) {
    return this.prisma.clinicVisit.create({
      data: { schoolId, attendedBy, ...dto, followUpDate: dto.followUpDate ? new Date(dto.followUpDate) : undefined },
    });
  }

  async updateVisit(id: string, dto: any) {
    return this.prisma.clinicVisit.update({ where: { id }, data: dto });
  }

  async getClinicStats(schoolId: string) {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const [totalRecords, visitsThisMonth, pendingFollowUps] = await Promise.all([
      this.prisma.medicalRecord.count({ where: { schoolId } }),
      this.prisma.clinicVisit.count({ where: { schoolId, visitDate: { gte: thirtyDaysAgo } } }),
      this.prisma.clinicVisit.count({ where: { schoolId, followUpDate: { gte: new Date() }, referral: null } }),
    ]);
    return { totalRecords, visitsThisMonth, pendingFollowUps };
  }
}

@Controller('clinic')
@UseGuards(JwtAuthGuard, PermissionsGuard)
class ClinicController {
  constructor(private readonly svc: ClinicService) {}

  @Get('stats') @RequirePermissions('clinic:clinic:READ') stats(@Req() r: any) { return this.svc.getClinicStats(r.user.schoolId); }
  @Get('visits') @RequirePermissions('clinic:clinic:READ') visits(@Req() r: any, @Query() q: any) { return this.svc.getVisits(r.user.schoolId, q); }
  @Post('visits') @RequirePermissions('clinic:clinic:CREATE') createVisit(@Req() r: any, @Body() b: any) { return this.svc.createVisit(r.user.schoolId, r.user.id, b); }
  @Put('visits/:id') @RequirePermissions('clinic:clinic:UPDATE') updateVisit(@Param('id') id: string, @Body() b: any) { return this.svc.updateVisit(id, b); }

  @Get('records/student/:studentId') @RequirePermissions('clinic:clinic:READ') getStudentRecord(@Param('studentId') id: string) { return this.svc.getMedicalRecord(id); }
  @Get('records/staff/:staffId') @RequirePermissions('clinic:clinic:READ') getStaffRecord(@Param('staffId') id: string) { return this.svc.getMedicalRecord(undefined, id); }
  @Post('records') @RequirePermissions('clinic:clinic:CREATE') upsertRecord(@Req() r: any, @Body() b: any) { return this.svc.upsertMedicalRecord({ schoolId: r.user.schoolId, ...b }); }
}

@Module({
  imports: [DatabaseModule],
  controllers: [ClinicController],
  providers: [ClinicService],
  exports: [ClinicService],
})
export class ClinicModule {}
