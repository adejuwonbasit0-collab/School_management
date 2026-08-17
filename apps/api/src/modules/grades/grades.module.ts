import { Module } from '@nestjs/common';
import { Injectable } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId, CurrentUser } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class GradesService {
  constructor(private readonly prisma: PrismaService) {}

  async getGrades(schoolId: string, query: any = {}) {
    const { studentId, subjectId, termId, classRoomId, page = 1, limit = 50 } = query;
    const where: any = { student: { schoolId }, ...(studentId && { studentId }), ...(subjectId && { subjectId }), ...(termId && { termId }) };
    const [data, total] = await Promise.all([
      this.prisma.grade.findMany({
        where, skip: (page-1)*limit, take: limit,
        include: { student: { include: { user: { select: { firstName: true, lastName: true } } } }, subject: { select: { name: true } } },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.grade.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }

  async saveGrades(schoolId: string, grades: any[], gradedById: string) {
    const saved = await Promise.all(
      grades.map((g) => this.prisma.grade.create({
        data: { studentId: g.studentId, subjectId: g.subjectId, termId: g.termId, gradedById, type: g.type, score: g.score, maxScore: g.maxScore || 100, weight: g.weight || 100, remarks: g.remarks },
      })),
    );
    return { saved: saved.length };
  }

  async getStudentGradeSummary(studentId: string, termId: string) {
    const grades = await this.prisma.grade.findMany({
      where: { studentId, termId },
      include: { subject: { select: { name: true } } },
    });
    const bySubject = grades.reduce((acc, g) => {
      const key = g.subjectId;
      if (!acc[key]) acc[key] = { subject: g.subject.name, grades: [], total: 0, count: 0 };
      const pct = (Number(g.score) / Number(g.maxScore)) * 100;
      acc[key].grades.push({ type: g.type, score: Number(g.score), maxScore: Number(g.maxScore), percentage: pct });
      acc[key].total += pct;
      acc[key].count++;
      return acc;
    }, {} as Record<string, any>);
    return Object.values(bySubject).map((s: any) => ({ ...s, average: s.total / s.count, grade: this.getGrade(s.total / s.count) }));
  }

  private getGrade(pct: number): string {
    if (pct >= 70) return 'A';
    if (pct >= 60) return 'B';
    if (pct >= 50) return 'C';
    if (pct >= 45) return 'D';
    return 'F';
  }
}

@ApiTags('Grades') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'grades', version: '1' })
export class GradesController {
  constructor(private readonly service: GradesService) {}
  @Get() @RequirePermissions('grades:grades:READ') getGrades(@SchoolId() sid: string, @Query() q: any) { return this.service.getGrades(sid, q); }
  @Post() @RequirePermissions('grades:grades:CREATE') saveGrades(@SchoolId() sid: string, @Body() body: any, @CurrentUser() user: any) { return this.service.saveGrades(sid, body.grades, user.staff?.teacherProfile?.id || user.id); }
  @Get('student/:studentId/summary') @RequirePermissions('grades:grades:READ') getSummary(@Param('studentId') sid: string, @Query('termId') termId: string) { return this.service.getStudentGradeSummary(sid, termId); }
}

@Module({ controllers: [GradesController], providers: [GradesService], exports: [GradesService] })
export class GradesModule {}
