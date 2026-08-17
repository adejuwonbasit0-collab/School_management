import { Module } from '@nestjs/common';
import { Injectable, Logger } from '@nestjs/common';
import { Controller, Get, Post, Body, Param, Query, Res, UseGuards } from '@nestjs/common';
import { Response } from 'express';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';
import PDFDocument from 'pdfkit';
import { format } from 'date-fns';

@Injectable()
export class ReportsService {
  private readonly logger = new Logger(ReportsService.name);

  constructor(private readonly prisma: PrismaService) {}

  async generateFeeReport(schoolId: string, options: { startDate: string; endDate: string }) {
    const school = await this.prisma.school.findUnique({ where: { id: schoolId }, select: { name: true, address: true, logo: true, currencySymbol: true } });

    const payments = await this.prisma.payment.findMany({
      where: {
        schoolId,
        status: 'COMPLETED',
        paidAt: { gte: new Date(options.startDate), lte: new Date(options.endDate) },
      },
      include: {
        invoice: {
          include: {
            student: { include: { user: { select: { firstName: true, lastName: true } }, enrollments: { where: { isCurrent: true }, include: { classRoom: { select: { name: true } } } } } },
          },
        },
      },
      orderBy: { paidAt: 'desc' },
    });

    const total = payments.reduce((sum, p) => sum + Number(p.amount), 0);
    const sym = school?.currencySymbol || '₦';

    return {
      school: school?.name,
      period: { start: options.startDate, end: options.endDate },
      totalCollected: total,
      totalTransactions: payments.length,
      payments: payments.map((p) => ({
        date: p.paidAt ? format(new Date(p.paidAt), 'dd/MM/yyyy') : '',
        student: `${p.invoice?.student?.user?.firstName} ${p.invoice?.student?.user?.lastName}`,
        class: p.invoice?.student?.enrollments?.[0]?.classRoom?.name || '',
        invoiceNo: p.invoice?.invoiceNo,
        amount: `${sym}${Number(p.amount).toLocaleString()}`,
        gateway: p.gateway,
        reference: p.transactionRef,
      })),
    };
  }

  async generateAttendanceReport(schoolId: string, options: { classRoomId?: string; termId: string }) {
    const whereClause: any = { schoolId, termId: options.termId };
    if (options.classRoomId) whereClause.classRoomId = options.classRoomId;

    const records = await this.prisma.attendance.groupBy({
      by: ['studentId', 'status'],
      where: whereClause,
      _count: true,
    });

    const studentIds = [...new Set(records.map((r) => r.studentId))];
    const students = await this.prisma.student.findMany({
      where: { id: { in: studentIds } },
      include: {
        user: { select: { firstName: true, lastName: true } },
        enrollments: { where: { isCurrent: true }, include: { classRoom: { select: { name: true, section: true } } } },
      },
    });

    const studentMap = new Map(students.map((s) => [s.id, s]));
    const summary = studentIds.map((studentId) => {
      const studentRecords = records.filter((r) => r.studentId === studentId);
      const total = studentRecords.reduce((sum, r) => sum + r._count, 0);
      const present = studentRecords.find((r) => r.status === 'PRESENT')?._count || 0;
      const absent = studentRecords.find((r) => r.status === 'ABSENT')?._count || 0;
      const late = studentRecords.find((r) => r.status === 'LATE')?._count || 0;
      const student = studentMap.get(studentId) as any;
      return {
        name: student ? `${student.user.firstName} ${student.user.lastName}` : '',
        class: student?.enrollments?.[0]?.classRoom?.name || '',
        total, present, absent, late,
        rate: total > 0 ? Math.round(((present + late) / total) * 100) : 0,
      };
    }).sort((a, b) => b.rate - a.rate);

    return { summary, totalStudents: studentIds.length };
  }

  async generateStudentResultCard(schoolId: string, studentId: string, examinationId: string) {
    const school = await this.prisma.school.findUnique({
      where: { id: schoolId },
      select: { name: true, address: true, logo: true, motto: true },
    });

    const result = await this.prisma.examResult.findUnique({
      where: { examinationId_studentId: { examinationId, studentId } },
      include: {
        student: {
          include: {
            user: { select: { firstName: true, lastName: true, avatar: true } },
            enrollments: { where: { isCurrent: true }, include: { classRoom: { select: { name: true } } } },
          },
        },
        examination: {
          include: { academicYear: { select: { name: true } }, term: { select: { name: true } } },
        },
      },
    });

    if (!result) return null;

    // Get class position
    const allResults = await this.prisma.examResult.findMany({
      where: { examinationId },
      orderBy: { percentage: 'desc' },
    });
    const position = allResults.findIndex((r) => r.studentId === studentId) + 1;

    return {
      school,
      student: {
        name: `${result.student.user.firstName} ${result.student.user.lastName}`,
        class: result.student.enrollments?.[0]?.classRoom?.name,
        admissionNo: result.student.admissionNo,
      },
      examination: {
        name: result.examination.name,
        academicYear: result.examination.academicYear?.name,
        term: result.examination.term?.name,
      },
      scores: result.scores,
      totalScore: result.totalScore,
      percentage: result.percentage,
      grade: result.grade,
      position,
      outOf: allResults.length,
      remarks: result.remarks,
      publishedAt: result.publishedAt,
    };
  }

  async getDashboardAnalytics(schoolId: string) {
    const currentYear = await this.prisma.academicYear.findFirst({
      where: { schoolId, isCurrent: true },
    });

    const [
      enrollmentByClass,
      feeCollectionByMonth,
      attendanceByClass,
      staffByDepartment,
    ] = await Promise.all([
      this.prisma.studentEnrollment.groupBy({
        by: ['classRoomId'],
        where: { student: { schoolId }, isCurrent: true },
        _count: true,
      }),
      this.prisma.payment.groupBy({
        by: [],
        where: { schoolId, status: 'COMPLETED', paidAt: { gte: new Date(new Date().getFullYear(), 0, 1) } },
        _sum: { amount: true },
        _count: true,
      }),
      this.prisma.attendance.groupBy({
        by: ['classRoomId', 'status'],
        where: { schoolId, date: { gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) } },
        _count: true,
      }),
      this.prisma.staff.groupBy({
        by: ['departmentId'],
        where: { schoolId, employmentStatus: 'ACTIVE' },
        _count: true,
      }),
    ]);

    return {
      enrollmentByClass,
      yearlyCollection: feeCollectionByMonth[0]?._sum?.amount || 0,
      attendanceSummary: attendanceByClass,
      staffByDepartment,
    };
  }
}

@ApiTags('Reports') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'reports', version: '1' })
export class ReportsController {
  constructor(private readonly reportsService: ReportsService) {}

  @Get('analytics') @RequirePermissions('reports:reports:READ')
  getAnalytics(@SchoolId() sid: string) {
    return this.reportsService.getDashboardAnalytics(sid);
  }

  @Get('fees') @RequirePermissions('reports:reports:READ')
  getFeeReport(@SchoolId() sid: string, @Query('startDate') start: string, @Query('endDate') end: string) {
    return this.reportsService.generateFeeReport(sid, { startDate: start, endDate: end });
  }

  @Get('attendance') @RequirePermissions('reports:reports:READ')
  getAttendanceReport(@SchoolId() sid: string, @Query() q: any) {
    return this.reportsService.generateAttendanceReport(sid, q);
  }

  @Get('result-card/:studentId') @RequirePermissions('reports:reports:READ')
  getResultCard(@SchoolId() sid: string, @Param('studentId') studentId: string, @Query('examinationId') examId: string) {
    return this.reportsService.generateStudentResultCard(sid, studentId, examId);
  }
}

@Module({ controllers: [ReportsController], providers: [ReportsService], exports: [ReportsService] })
export class ReportsModule {}
