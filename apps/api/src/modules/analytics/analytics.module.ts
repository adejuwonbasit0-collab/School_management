import { Module } from '@nestjs/common';
import { Injectable } from '@nestjs/common';
import { Controller, Get, Param, Query, Req, Res, UseGuards } from '@nestjs/common';
import { Response } from 'express';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';
import { DatabaseModule } from '../../database/database.module';
import * as ExcelJS from 'exceljs';

@Injectable()
class AnalyticsService {
  constructor(private prisma: PrismaService) {}

  async getExecutiveDashboard(schoolId: string) {
    const now = new Date();
    const thisMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);

    const [
      totalStudents, newStudentsThisMonth, totalStaff, activeStaff,
      revenueThisMonth, revenueLastMonth, unpaidInvoices,
      attendanceToday, totalClasses, pendingAdmissions,
    ] = await Promise.all([
      this.prisma.student.count({ where: { schoolId } }),
      this.prisma.student.count({ where: { schoolId, createdAt: { gte: thisMonth } } }),
      this.prisma.staff.count({ where: { schoolId } }),
      this.prisma.staff.count({ where: { schoolId, employmentStatus: 'ACTIVE' } }),
      this.prisma.payment.aggregate({ where: { schoolId, status: 'COMPLETED', createdAt: { gte: thisMonth } }, _sum: { amount: true } }),
      this.prisma.payment.aggregate({ where: { schoolId, status: 'COMPLETED', createdAt: { gte: lastMonth, lte: lastMonthEnd } }, _sum: { amount: true } }),
      this.prisma.feeInvoice.count({ where: { schoolId, status: { in: ['UNPAID', 'OVERDUE'] } } }),
      this.prisma.attendance.count({ where: { schoolId, date: { gte: new Date(now.setHours(0,0,0,0)) }, status: 'PRESENT' } }),
      this.prisma.classRoom.count({ where: { schoolId, isActive: true } }),
      this.prisma.admission.count({ where: { schoolId, status: 'PENDING' } }),
    ]);

    const thisMonthRev = Number(revenueThisMonth._sum.amount || 0);
    const lastMonthRev = Number(revenueLastMonth._sum.amount || 0);
    const revenueGrowth = lastMonthRev > 0 ? ((thisMonthRev - lastMonthRev) / lastMonthRev) * 100 : 0;

    return {
      students: { total: totalStudents, newThisMonth: newStudentsThisMonth },
      staff: { total: totalStaff, active: activeStaff },
      finance: { revenueThisMonth: thisMonthRev, revenueLastMonth: lastMonthRev, revenueGrowth: revenueGrowth.toFixed(1), unpaidInvoices },
      attendance: { presentToday: attendanceToday },
      academic: { totalClasses },
      admissions: { pending: pendingAdmissions },
    };
  }

  async getRevenueAnalytics(schoolId: string, query: { year?: number; months?: number }) {
    const year = query.year || new Date().getFullYear();
    const months = query.months || 12;

    const results = [];
    for (let m = 0; m < months; m++) {
      const start = new Date(year, m, 1);
      const end = new Date(year, m + 1, 0, 23, 59, 59);
      const [collected, invoiced] = await Promise.all([
        this.prisma.payment.aggregate({ where: { schoolId, status: 'COMPLETED', createdAt: { gte: start, lte: end } }, _sum: { amount: true } }),
        this.prisma.feeInvoice.aggregate({ where: { schoolId, createdAt: { gte: start, lte: end } }, _sum: { totalAmount: true } }),
      ]);
      results.push({
        month: start.toLocaleString('default', { month: 'short' }),
        year,
        collected: Number(collected._sum.amount || 0),
        invoiced: Number(invoiced._sum.totalAmount || 0),
      });
    }
    return results;
  }

  async getStudentAnalytics(schoolId: string) {
    const [byGender, byClass, enrollmentTrend, statusBreakdown] = await Promise.all([
      this.prisma.user.groupBy({ by: ['gender'], where: { schoolId, student: { isNot: null } }, _count: true }),
      this.prisma.studentEnrollment.groupBy({ by: ['classRoomId'], where: { classRoom: { schoolId }, isCurrent: true }, _count: true }),
      // Monthly enrollment over last 6 months
      Promise.all(Array.from({ length: 6 }, (_, i) => {
        const d = new Date(); d.setMonth(d.getMonth() - i);
        const start = new Date(d.getFullYear(), d.getMonth(), 1);
        const end = new Date(d.getFullYear(), d.getMonth() + 1, 0);
        return this.prisma.student.count({ where: { schoolId, createdAt: { gte: start, lte: end } } })
          .then(count => ({ month: start.toLocaleString('default', { month: 'short' }), count }));
      })),
      this.prisma.student.groupBy({ by: ['status'], where: { schoolId }, _count: true }),
    ]);

    return { byGender, byClass, enrollmentTrend: enrollmentTrend.reverse(), statusBreakdown };
  }

  async getAttendanceAnalytics(schoolId: string, query: { classRoomId?: string; weeks?: number }) {
    const weeks = query.weeks || 4;
    const since = new Date(Date.now() - weeks * 7 * 24 * 60 * 60 * 1000);
    const where: any = { schoolId, date: { gte: since } };
    if (query.classRoomId) where.classRoomId = query.classRoomId;

    const records = await this.prisma.attendance.groupBy({
      by: ['status'],
      where,
      _count: true,
    });

    const daily = await this.prisma.attendance.groupBy({
      by: ['date', 'status'],
      where: { ...where, date: { gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) } },
      _count: true,
      orderBy: { date: 'asc' },
    });

    return { summary: records, daily };
  }

  async getAcademicPerformanceAnalytics(schoolId: string) {
    const recentExams = await this.prisma.examination.findMany({
      where: { schoolId, status: 'RESULTS_PUBLISHED' },
      include: {
        results: { select: { percentage: true, grade: true } },
        term: { select: { name: true } },
      },
      orderBy: { createdAt: 'desc' },
      take: 10,
    });

    return recentExams.map(exam => {
      const percentages = exam.results.map(r => Number(r.percentage));
      const avg = percentages.length ? percentages.reduce((a, b) => a + b, 0) / percentages.length : 0;
      const passing = percentages.filter(p => p >= 50).length;
      const passRate = percentages.length ? (passing / percentages.length) * 100 : 0;
      return {
        examId: exam.id,
        examName: exam.name,
        term: exam.term?.name,
        studentCount: exam.results.length,
        averageScore: avg.toFixed(1),
        passRate: passRate.toFixed(1),
      };
    });
  }

  async getFinanceReport(schoolId: string, query: { from?: string; to?: string }) {
    const where: any = { schoolId };
    if (query.from) where.createdAt = { ...(where.createdAt || {}), gte: new Date(query.from) };
    if (query.to) where.createdAt = { ...(where.createdAt || {}), lte: new Date(query.to) };

    const [invoices, payments, byStatus, byGateway, topDebtors] = await Promise.all([
      this.prisma.feeInvoice.aggregate({ where, _sum: { totalAmount: true }, _count: true }),
      this.prisma.payment.aggregate({ where: { ...where, status: 'COMPLETED' }, _sum: { amount: true }, _count: true }),
      this.prisma.feeInvoice.groupBy({ by: ['status'], where, _count: true, _sum: { totalAmount: true } }),
      this.prisma.payment.groupBy({ by: ['gateway'], where: { ...where, status: 'COMPLETED' }, _count: true, _sum: { amount: true } }),
      this.prisma.feeInvoice.findMany({
        where: { ...where, status: { in: ['UNPAID', 'OVERDUE', 'PARTIAL'] } },
        include: { student: { include: { user: { select: { firstName: true, lastName: true } } } } },
        orderBy: { totalAmount: 'desc' },
        take: 10,
      }),
    ]);

    return { invoices, payments, byStatus, byGateway, topDebtors };
  }

  async exportReport(schoolId: string, type: string, query: any, res: Response) {
    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'EduCore';
    workbook.created = new Date();

    if (type === 'finance') {
      const data = await this.getFinanceReport(schoolId, query);
      const sheet = workbook.addWorksheet('Finance Report');
      sheet.addRow(['Status', 'Count', 'Total Amount']);
      (data.byStatus || []).forEach((r: any) => sheet.addRow([r.status, r._count, r._sum.totalAmount]));
    } else if (type === 'students') {
      const students = await this.prisma.student.findMany({
        where: { schoolId },
        include: { user: { select: { firstName: true, lastName: true, email: true, gender: true } }, enrollments: { where: { isCurrent: true }, include: { classRoom: true } } },
      });
      const sheet = workbook.addWorksheet('Students');
      sheet.addRow(['Admission No', 'First Name', 'Last Name', 'Email', 'Gender', 'Class', 'Status']);
      students.forEach(s => sheet.addRow([s.admissionNo, s.user?.firstName, s.user?.lastName, s.user?.email, s.user?.gender, s.enrollments[0]?.classRoom?.name, s.status]));
    } else if (type === 'attendance') {
      const attendance = await this.prisma.attendance.findMany({
        where: { schoolId, date: { gte: new Date(query.from || Date.now() - 30 * 24 * 60 * 60 * 1000) } },
        include: { student: { include: { user: { select: { firstName: true, lastName: true } } } }, classRoom: true },
        orderBy: { date: 'desc' },
        take: 1000,
      });
      const sheet = workbook.addWorksheet('Attendance');
      sheet.addRow(['Date', 'Student', 'Class', 'Status', 'Remarks']);
      attendance.forEach(a => sheet.addRow([a.date.toLocaleDateString(), `${a.student?.user?.firstName} ${a.student?.user?.lastName}`, a.classRoom?.name, a.status, a.remarks]));
    }

    res.set({ 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Content-Disposition': `attachment; filename="${type}-report.xlsx"` });
    await workbook.xlsx.write(res);
    res.end();
  }
}

@Controller('analytics')
@UseGuards(JwtAuthGuard, PermissionsGuard)
class AnalyticsController {
  constructor(private readonly svc: AnalyticsService) {}

  @Get('dashboard') @RequirePermissions('analytics:analytics:READ') dashboard(@Req() r: any) { return this.svc.getExecutiveDashboard(r.user.schoolId); }
  @Get('revenue') @RequirePermissions('analytics:analytics:READ') revenue(@Req() r: any, @Query() q: any) { return this.svc.getRevenueAnalytics(r.user.schoolId, q); }
  @Get('students') @RequirePermissions('analytics:analytics:READ') students(@Req() r: any) { return this.svc.getStudentAnalytics(r.user.schoolId); }
  @Get('attendance') @RequirePermissions('analytics:analytics:READ') attendance(@Req() r: any, @Query() q: any) { return this.svc.getAttendanceAnalytics(r.user.schoolId, q); }
  @Get('academic') @RequirePermissions('analytics:analytics:READ') academic(@Req() r: any) { return this.svc.getAcademicPerformanceAnalytics(r.user.schoolId); }
  @Get('finance') @RequirePermissions('analytics:analytics:READ') finance(@Req() r: any, @Query() q: any) { return this.svc.getFinanceReport(r.user.schoolId, q); }

  @Get('export/:type') @RequirePermissions('analytics:analytics:READ')
  async export(@Param('type') type: string, @Req() r: any, @Query() q: any, @Res() res: Response) {
    return this.svc.exportReport(r.user.schoolId, type, q, res);
  }
}

@Module({
  imports: [DatabaseModule],
  controllers: [AnalyticsController],
  providers: [AnalyticsService],
  exports: [AnalyticsService],
})
export class AnalyticsModule {}
