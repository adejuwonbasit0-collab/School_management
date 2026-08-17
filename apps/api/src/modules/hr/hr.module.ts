import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId, CurrentUser } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';
import { EventEmitter2 } from '@nestjs/event-emitter';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class HrService {
  constructor(private readonly prisma: PrismaService, private readonly eventEmitter: EventEmitter2) {}

  async getStaff(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20, search, departmentId, employmentStatus } = query;
    const where: any = {
      schoolId,
      ...(employmentStatus && { employmentStatus }),
      ...(departmentId && { departmentId }),
      ...(search && {
        OR: [
          { staffId: { contains: search, mode: 'insensitive' } },
          { user: { firstName: { contains: search, mode: 'insensitive' } } },
          { user: { lastName: { contains: search, mode: 'insensitive' } } },
          { user: { email: { contains: search, mode: 'insensitive' } } },
        ],
      }),
    };
    const [data, total] = await Promise.all([
      this.prisma.staff.findMany({
        where, skip: (page-1)*limit, take: limit,
        include: {
          user: { select: { id: true, firstName: true, lastName: true, email: true, phone: true, avatar: true, gender: true, status: true } },
          department: { select: { id: true, name: true } },
          teacherProfile: { select: { id: true } },
        },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.staff.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }

  async getStaffMember(schoolId: string, id: string) {
    const staff = await this.prisma.staff.findFirst({
      where: { id, schoolId },
      include: {
        user: true,
        department: true,
        teacherProfile: { include: { subjects: { include: { subject: true } } } },
        leaveRecords: { orderBy: { createdAt: 'desc' }, take: 10 },
        payrollRecords: { orderBy: { createdAt: 'desc' }, take: 12 },
      },
    });
    if (!staff) throw new NotFoundException('Staff not found');
    return staff;
  }

  async createStaff(schoolId: string, data: any) {
    const passwordHash = await bcrypt.hash(data.password || 'Staff2024!', 12);
    return this.prisma.$transaction(async (tx) => {
      const user = await tx.user.create({
        data: {
          schoolId,
          email: data.email.toLowerCase(),
          passwordHash,
          firstName: data.firstName,
          lastName: data.lastName,
          phone: data.phone,
          gender: data.gender,
          dateOfBirth: data.dateOfBirth ? new Date(data.dateOfBirth) : undefined,
          status: 'ACTIVE',
        },
      });
      const staffCount = await tx.staff.count({ where: { schoolId } });
      const staffId = `STF${new Date().getFullYear().toString().slice(-2)}${String(staffCount + 1).padStart(4, '0')}`;
      const staff = await tx.staff.create({
        data: {
          userId: user.id,
          schoolId,
          staffId,
          departmentId: data.departmentId,
          position: data.position,
          qualification: data.qualification,
          specialization: data.specialization,
          employmentType: data.employmentType || 'FULL_TIME',
          joiningDate: data.joiningDate ? new Date(data.joiningDate) : new Date(),
          salary: data.salary,
          bankName: data.bankName,
          bankAccountNo: data.bankAccountNo,
          bankAccountName: data.bankAccountName,
        },
      });
      // If teacher, create teacher profile
      if (data.isTeacher) {
        await tx.teacher.create({ data: { staffId: staff.id } });
        const teacherRole = await tx.role.findFirst({ where: { schoolId, slug: 'teacher' } });
        if (teacherRole) await tx.userRole.create({ data: { userId: user.id, roleId: teacherRole.id } });
      }
      return staff;
    });
  }

  async updateStaff(schoolId: string, id: string, data: any) {
    const staff = await this.prisma.staff.findFirst({ where: { id, schoolId } });
    if (!staff) throw new NotFoundException('Staff not found');
    await this.prisma.$transaction([
      this.prisma.user.update({ where: { id: staff.userId }, data: { firstName: data.firstName, lastName: data.lastName, phone: data.phone, gender: data.gender, avatar: data.avatar } }),
      this.prisma.staff.update({ where: { id }, data: { departmentId: data.departmentId, position: data.position, employmentStatus: data.employmentStatus, salary: data.salary } }),
    ]);
    return this.getStaffMember(schoolId, id);
  }

  // Leave
  async getLeaveRecords(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20, status } = query;
    const [data, total] = await Promise.all([
      this.prisma.leaveRecord.findMany({
        where: { staff: { schoolId }, ...(status && { status }) },
        skip: (page-1)*limit, take: limit,
        include: { staff: { include: { user: { select: { firstName: true, lastName: true, avatar: true } } } } },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.leaveRecord.count({ where: { staff: { schoolId }, ...(status && { status }) } }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }

  async createLeaveRequest(staffId: string, data: any) {
    const start = new Date(data.startDate);
    const end = new Date(data.endDate);
    const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    return this.prisma.leaveRecord.create({
      data: { staffId, type: data.type, startDate: start, endDate: end, days, reason: data.reason, status: 'PENDING' },
    });
  }

  async approveLeave(id: string, approvedBy: string, status: 'APPROVED' | 'REJECTED', remarks?: string) {
    return this.prisma.leaveRecord.update({
      where: { id },
      data: { status, approvedBy, approvedAt: new Date(), remarks },
    });
  }

  // Payroll
  async getPayrollRecords(schoolId: string, query: any = {}) {
    const { month, year } = query;
    return this.prisma.payrollRecord.findMany({
      where: { staff: { schoolId }, ...(month && { month: Number(month) }), ...(year && { year: Number(year) }) },
      include: { staff: { include: { user: { select: { firstName: true, lastName: true, avatar: true } } } } },
      orderBy: [{ year: 'desc' }, { month: 'desc' }],
    });
  }

  async generatePayroll(schoolId: string, month: number, year: number) {
    const activeStaff = await this.prisma.staff.findMany({
      where: { schoolId, employmentStatus: 'ACTIVE' },
      select: { id: true, salary: true },
    });
    const records = await Promise.all(
      activeStaff.map(async (staff) => {
        const existing = await this.prisma.payrollRecord.findUnique({ where: { staffId_month_year: { staffId: staff.id, month, year } } });
        if (existing) return existing;
        const basicSalary = Number(staff.salary || 0);
        const allowances = { housing: basicSalary * 0.2, transport: basicSalary * 0.1 };
        const totalAllowances = Object.values(allowances).reduce((a, b) => a + b, 0);
        const deductions = { tax: basicSalary * 0.075, pension: basicSalary * 0.08 };
        const totalDeductions = Object.values(deductions).reduce((a, b) => a + b, 0);
        const grossSalary = basicSalary + totalAllowances;
        const netSalary = grossSalary - totalDeductions;
        return this.prisma.payrollRecord.create({
          data: { staffId: staff.id, month, year, basicSalary, allowances, deductions, grossSalary, netSalary, status: 'PENDING' },
        });
      }),
    );
    return { generated: records.length, month, year };
  }


  async getSalaryStructures(schoolId: string) {
    return this.prisma.salaryStructure.findMany({ where: { schoolId }, orderBy: { name: 'asc' } });
  }

  async createSalaryStructure(schoolId: string, dto: any) {
    if (dto.isDefault) {
      await this.prisma.salaryStructure.updateMany({ where: { schoolId }, data: { isDefault: false } });
    }
    return this.prisma.salaryStructure.create({ data: { schoolId, ...dto } });
  }

  async updateSalaryStructure(id: string, schoolId: string, dto: any) {
    const s = await this.prisma.salaryStructure.findFirst({ where: { id, schoolId } });
    if (!s) throw new Error('Not found');
    return this.prisma.salaryStructure.update({ where: { id }, data: dto });
  }

  async getPerformanceReviews(schoolId: string) {
    return this.prisma.performanceReview.findMany({
      where: { staff: { schoolId } },
      include: { staff: { include: { user: { select: { firstName: true, lastName: true } } } } },
      orderBy: { createdAt: 'desc' },
    });
  }

  async createPerformanceReview(schoolId: string, reviewedBy: string, dto: any) {
    const scores: Record<string, number> = dto.scores || {};
    const values = Object.values(scores) as number[];
    const totalScore = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
    const grade = totalScore >= 90 ? 'A' : totalScore >= 75 ? 'B' : totalScore >= 60 ? 'C' : 'D';
    return this.prisma.performanceReview.create({
      data: { ...dto, reviewedBy, totalScore, grade },
    });
  }

  async createDisciplinaryRecord(dto: any) {
    return this.prisma.disciplinaryRecord.create({ data: dto });
  }

  async getHrStats(schoolId: string) {
    const [total, active, onLeave, byDept] = await Promise.all([
      this.prisma.staff.count({ where: { schoolId } }),
      this.prisma.staff.count({ where: { schoolId, employmentStatus: 'ACTIVE' } }),
      this.prisma.leaveRecord.count({ where: { staff: { schoolId }, status: 'APPROVED', startDate: { lte: new Date() }, endDate: { gte: new Date() } } }),
      this.prisma.staff.groupBy({ by: ['departmentId'], where: { schoolId }, _count: true }),
    ]);
    return { total, active, onLeave, byDepartment: byDept };
  }
}

@ApiTags('HR') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'hr', version: '1' })
export class HrController {
  constructor(private readonly hrService: HrService) {}

  @Get('stats') @RequirePermissions('hr:staff:READ')
  getStats(@SchoolId() sid: string) { return this.hrService.getHrStats(sid); }

  @Get('staff') @RequirePermissions('hr:staff:READ')
  getStaff(@SchoolId() sid: string, @Query() q: any) { return this.hrService.getStaff(sid, q); }

  @Get('staff/:id') @RequirePermissions('hr:staff:READ')
  getStaffMember(@SchoolId() sid: string, @Param('id') id: string) { return this.hrService.getStaffMember(sid, id); }

  @Post('staff') @RequirePermissions('hr:staff:CREATE')
  createStaff(@SchoolId() sid: string, @Body() d: any) { return this.hrService.createStaff(sid, d); }

  @Put('staff/:id') @RequirePermissions('hr:staff:UPDATE')
  updateStaff(@SchoolId() sid: string, @Param('id') id: string, @Body() d: any) { return this.hrService.updateStaff(sid, id, d); }

  @Get('leave') @RequirePermissions('hr:leave:READ')
  getLeave(@SchoolId() sid: string, @Query() q: any) { return this.hrService.getLeaveRecords(sid, q); }

  @Post('leave') @RequirePermissions('hr:leave:CREATE')
  createLeave(@CurrentUser() user: any, @Body() d: any) { return this.hrService.createLeaveRequest(user.staff?.id, d); }

  @Put('leave/:id/approve') @RequirePermissions('hr:leave:APPROVE')
  approveLeave(@Param('id') id: string, @CurrentUser('id') userId: string, @Body() body: any) {
    return this.hrService.approveLeave(id, userId, body.status, body.remarks);
  }

  @Get('payroll') @RequirePermissions('hr:payroll:READ')
  getPayroll(@SchoolId() sid: string, @Query() q: any) { return this.hrService.getPayrollRecords(sid, q); }

  @Post('payroll/generate') @RequirePermissions('hr:payroll:CREATE')
  generatePayroll(@SchoolId() sid: string, @Body() body: { month: number; year: number }) {
    return this.hrService.generatePayroll(sid, body.month, body.year);
  }
  @Get('salary-structures') @RequirePermissions('hr:payroll:READ')
  getSalaryStructures(@SchoolId() sid: string) { return this.hrService.getSalaryStructures(sid); }

  @Post('salary-structures') @RequirePermissions('hr:payroll:CREATE')
  createSalaryStructure(@SchoolId() sid: string, @Body() d: any) { return this.hrService.createSalaryStructure(sid, d); }

  @Put('salary-structures/:id') @RequirePermissions('hr:payroll:UPDATE')
  updateSalaryStructure(@SchoolId() sid: string, @Param('id') id: string, @Body() d: any) { return this.hrService.updateSalaryStructure(id, sid, d); }

  @Get('performance-reviews') @RequirePermissions('hr:staff:READ')
  getReviews(@SchoolId() sid: string) { return this.hrService.getPerformanceReviews(sid); }

  @Post('performance-reviews') @RequirePermissions('hr:staff:CREATE')
  createReview(@SchoolId() sid: string, @CurrentUser('id') uid: string, @Body() d: any) { return this.hrService.createPerformanceReview(sid, uid, d); }

  @Post('payroll/:id/pdf') @RequirePermissions('hr:payroll:READ')
  downloadPayslip(@Param('id') id: string) { return { url: `/hr/payroll/${id}/pdf` }; }


}

@Module({ controllers: [HrController], providers: [HrService], exports: [HrService] })
export class HrModule {}
