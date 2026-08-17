import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { EventEmitter2 } from '@nestjs/event-emitter';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class ExaminationsService {
  constructor(private readonly prisma: PrismaService, private readonly events: EventEmitter2) {}

  async findAll(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20 } = query;
    const [data, total] = await Promise.all([
      this.prisma.examination.findMany({
        where: { schoolId }, skip: (page-1)*limit, take: limit,
        include: { term: { select: { name: true } }, academicYear: { select: { name: true } }, _count: { select: { results: true, schedules: true } } },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.examination.count({ where: { schoolId } }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }

  async findOne(schoolId: string, id: string) {
    const exam = await this.prisma.examination.findFirst({
      where: { id, schoolId },
      include: { term: true, academicYear: true, schedules: true, _count: { select: { results: true } } },
    });
    if (!exam) throw new NotFoundException('Examination not found');
    return exam;
  }

  async create(schoolId: string, data: any) {
    return this.prisma.examination.create({
      data: { schoolId, name: data.name, type: data.type, academicYearId: data.academicYearId, termId: data.termId, startDate: data.startDate ? new Date(data.startDate) : undefined, endDate: data.endDate ? new Date(data.endDate) : undefined, instructions: data.instructions, status: 'DRAFT' },
    });
  }

  async updateStatus(id: string, status: string) {
    return this.prisma.examination.update({ where: { id }, data: { status: status as any } });
  }

  async publishResults(schoolId: string, id: string) {
    const exam = await this.prisma.examination.findFirst({ where: { id, schoolId } });
    if (!exam) throw new NotFoundException('Examination not found');
    await this.prisma.$transaction([
      this.prisma.examination.update({ where: { id }, data: { status: 'RESULTS_PUBLISHED' } }),
      this.prisma.examResult.updateMany({ where: { examinationId: id }, data: { publishedAt: new Date() } }),
    ]);
    this.events.emit('examination.results_published', { examinationId: id, schoolId });
    return { message: 'Results published successfully' };
  }

  async saveResults(schoolId: string, examinationId: string, results: any[]) {
    const exam = await this.prisma.examination.findFirst({ where: { id: examinationId, schoolId } });
    if (!exam) throw new NotFoundException('Examination not found');
    const saved = await Promise.all(
      results.map((r) => this.prisma.examResult.upsert({
        where: { examinationId_studentId: { examinationId, studentId: r.studentId } },
        create: { examinationId, studentId: r.studentId, scores: r.scores, totalScore: r.totalScore, percentage: r.percentage, grade: r.grade, position: r.position, remarks: r.remarks },
        update: { scores: r.scores, totalScore: r.totalScore, percentage: r.percentage, grade: r.grade, position: r.position, remarks: r.remarks },
      })),
    );
    if (exam.status === 'DRAFT' || exam.status === 'PUBLISHED') {
      await this.prisma.examination.update({ where: { id: examinationId }, data: { status: 'COMPLETED' } });
    }
    return { saved: saved.length };
  }

  async getResults(schoolId: string, examinationId: string) {
    return this.prisma.examResult.findMany({
      where: { examinationId, examination: { schoolId } },
      include: { student: { include: { user: { select: { firstName: true, lastName: true, avatar: true } }, enrollments: { where: { isCurrent: true }, include: { classRoom: { select: { name: true } } } } } } },
      orderBy: [{ position: 'asc' }, { percentage: 'desc' }],
    });
  }
}

@ApiTags('Examinations') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'examinations', version: '1' })
export class ExaminationsController {
  constructor(private readonly service: ExaminationsService) {}
  @Get() @RequirePermissions('examinations:examinations:READ') findAll(@SchoolId() sid: string, @Query() q: any) { return this.service.findAll(sid, q); }
  @Get(':id') @RequirePermissions('examinations:examinations:READ') findOne(@SchoolId() sid: string, @Param('id') id: string) { return this.service.findOne(sid, id); }
  @Post() @RequirePermissions('examinations:examinations:CREATE') create(@SchoolId() sid: string, @Body() d: any) { return this.service.create(sid, d); }
  @Put(':id/status') @RequirePermissions('examinations:examinations:UPDATE') updateStatus(@Param('id') id: string, @Body() body: any) { return this.service.updateStatus(id, body.status); }
  @Put(':id/publish') @RequirePermissions('examinations:examinations:UPDATE') publishResults(@SchoolId() sid: string, @Param('id') id: string) { return this.service.publishResults(sid, id); }
  @Post(':id/results') @RequirePermissions('examinations:examinations:UPDATE') saveResults(@SchoolId() sid: string, @Param('id') id: string, @Body() body: any) { return this.service.saveResults(sid, id, body.results); }
  @Get(':id/results') @RequirePermissions('examinations:examinations:READ') getResults(@SchoolId() sid: string, @Param('id') id: string) { return this.service.getResults(sid, id); }
}

@Module({ controllers: [ExaminationsController], providers: [ExaminationsService], exports: [ExaminationsService] })
export class ExaminationsModule {}
