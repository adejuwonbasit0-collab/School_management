import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { EventEmitter2 } from '@nestjs/event-emitter';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId, CurrentUser } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class AdmissionsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  async findAll(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20, search, status } = query;
    const skip = (page - 1) * limit;
    const where: any = {
      schoolId,
      ...(status && { status }),
      ...(search && { OR: [
        { applicationNo: { contains: search, mode: 'insensitive' } },
        { student: { user: { firstName: { contains: search, mode: 'insensitive' } } } },
        { student: { user: { lastName: { contains: search, mode: 'insensitive' } } } },
      ] }),
    };
    const [data, total] = await Promise.all([
      this.prisma.admissionRecord.findMany({
        where, skip, take: limit,
        include: { student: { include: { user: { select: { firstName: true, lastName: true, email: true, avatar: true } } } } },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.admissionRecord.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total / limit) } };
  }

  async findOne(schoolId: string, id: string) {
    const record = await this.prisma.admissionRecord.findFirst({
      where: { id, schoolId },
      include: { student: { include: { user: true, parents: { include: { parent: { include: { user: true } } } } } } },
    });
    if (!record) throw new NotFoundException('Admission record not found');
    return record;
  }

  async create(schoolId: string, data: any) {
    const count = await this.prisma.admissionRecord.count({ where: { schoolId } });
    const applicationNo = `APP${new Date().getFullYear()}${String(count + 1).padStart(5, '0')}`;
    return this.prisma.admissionRecord.create({
      data: { schoolId, studentId: data.studentId, applicationNo, status: 'SUBMITTED', appliedClass: data.appliedClass, academicYear: data.academicYear, documents: data.documents ?? {}, formData: data.formData ?? {} },
    });
  }

  async updateStatus(schoolId: string, id: string, status: string, data: any = {}, updatedBy: string) {
    const record = await this.prisma.admissionRecord.findFirst({ where: { id, schoolId } });
    if (!record) throw new NotFoundException('Record not found');
    const updated = await this.prisma.admissionRecord.update({
      where: { id },
      data: {
        status: status as any,
        ...(status === 'ADMITTED' && { admittedById: updatedBy, admittedAt: new Date() }),
        ...(status === 'REJECTED' && { rejectionReason: data.reason }),
        ...(data.interviewDate && { interviewDate: new Date(data.interviewDate) }),
        ...(data.interviewNotes && { interviewNotes: data.interviewNotes }),
      },
    });
    this.eventEmitter.emit('admission.status_changed', { admissionId: id, schoolId, studentId: record.studentId, status, updatedBy });
    return updated;
  }

  async getStats(schoolId: string) {
    const [total, submitted, underReview, admitted, rejected] = await Promise.all([
      this.prisma.admissionRecord.count({ where: { schoolId } }),
      this.prisma.admissionRecord.count({ where: { schoolId, status: 'SUBMITTED' } }),
      this.prisma.admissionRecord.count({ where: { schoolId, status: 'UNDER_REVIEW' } }),
      this.prisma.admissionRecord.count({ where: { schoolId, status: 'ADMITTED' } }),
      this.prisma.admissionRecord.count({ where: { schoolId, status: 'REJECTED' } }),
    ]);
    return { total, submitted, underReview, admitted, rejected };
  }
}

@ApiTags('Admissions') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'admissions', version: '1' })
export class AdmissionsController {
  constructor(private readonly service: AdmissionsService) {}
  @Get('stats') @RequirePermissions('admissions:admissions:READ')
  getStats(@SchoolId() sid: string) { return this.service.getStats(sid); }
  @Get() @RequirePermissions('admissions:admissions:READ')
  findAll(@SchoolId() sid: string, @Query() q: any) { return this.service.findAll(sid, q); }
  @Get(':id') @RequirePermissions('admissions:admissions:READ')
  findOne(@SchoolId() sid: string, @Param('id') id: string) { return this.service.findOne(sid, id); }
  @Post() @RequirePermissions('admissions:admissions:CREATE')
  create(@SchoolId() sid: string, @Body() d: any) { return this.service.create(sid, d); }
  @Put(':id/status') @RequirePermissions('admissions:admissions:APPROVE')
  updateStatus(@SchoolId() sid: string, @Param('id') id: string, @Body() body: any, @CurrentUser('id') userId: string) {
    return this.service.updateStatus(sid, id, body.status, body, userId);
  }
}

@Module({ controllers: [AdmissionsController], providers: [AdmissionsService], exports: [AdmissionsService] })
export class AdmissionsModule {}
