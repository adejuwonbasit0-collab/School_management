import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';

@Injectable()
export class SchoolsService {
  constructor(private readonly prisma: PrismaService) {}

  async getSettings(schoolId: string) {
    const school = await this.prisma.school.findUnique({ where: { id: schoolId } });
    if (!school) throw new NotFoundException('School not found');
    return school;
  }

  async updateSettings(schoolId: string, data: any) {
    return this.prisma.school.update({
      where: { id: schoolId },
      data: {
        name: data.name,
        email: data.email,
        phone: data.phone,
        website: data.website,
        address: data.address,
        city: data.city,
        state: data.state,
        country: data.country,
        description: data.description,
        timezone: data.timezone,
        currency: data.currency,
        currencySymbol: data.currencySymbol,
        motto: data.motto,
        registrationNo: data.registrationNo,
        establishedYear: data.establishedYear,
        logo: data.logo,
        favicon: data.favicon,
        tagline: data.tagline,
        colors: data.colors,
        socialLinks: data.socialLinks,
        seoMeta: data.seoMeta,
      },
    });
  }

  async getDashboard(schoolId: string) {
    const currentYear = await this.prisma.academicYear.findFirst({
      where: { schoolId, isCurrent: true },
    });

    const [totalStudents, totalStaff, totalClasses, totalSubjects, pendingAdmissions] =
      await Promise.all([
        this.prisma.student.count({ where: { schoolId } }),
        this.prisma.staff.count({ where: { schoolId, employmentStatus: 'ACTIVE' } }),
        this.prisma.classRoom.count({ where: { schoolId, isActive: true } }),
        this.prisma.subject.count({ where: { schoolId, isActive: true } }),
        this.prisma.admissionRecord.count({
          where: { schoolId, status: { in: ['SUBMITTED', 'UNDER_REVIEW'] } },
        }),
      ]);

    // Today's attendance
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const [todayPresent, todayTotal] = await Promise.all([
      this.prisma.attendance.count({
        where: { schoolId, date: today, status: { in: ['PRESENT', 'LATE'] } },
      }),
      this.prisma.attendance.count({ where: { schoolId, date: today } }),
    ]);

    // Last 7 days attendance trend
    const attendanceTrend = await Promise.all(
      Array.from({ length: 7 }, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (6 - i));
        d.setHours(0, 0, 0, 0);
        const next = new Date(d);
        next.setDate(next.getDate() + 1);
        return this.prisma.attendance.groupBy({
          by: ['status'],
          where: { schoolId, date: { gte: d, lt: next } },
          _count: true,
        }).then((res) => ({
          date: d.toLocaleDateString('en-US', { weekday: 'short' }),
          present: res.find((r) => r.status === 'PRESENT')?._count || 0,
          absent: res.find((r) => r.status === 'ABSENT')?._count || 0,
        }));
      }),
    );

    return {
      totalStudents,
      totalStaff,
      totalClasses,
      totalSubjects,
      pendingAdmissions,
      todayAttendanceRate: todayTotal > 0 ? Math.round((todayPresent / todayTotal) * 100) : 0,
      attendanceTrend,
      currentAcademicYear: currentYear?.name,
    };
  }

  // ─── Academic Years ──────────────────────────────────────────────────────────
  async getAcademicYears(schoolId: string) {
    return this.prisma.academicYear.findMany({
      where: { schoolId },
      include: {
        terms: { orderBy: { startDate: 'asc' } },
        _count: { select: { students: true } },
      },
      orderBy: { startDate: 'desc' },
    });
  }

  async createAcademicYear(schoolId: string, data: any) {
    return this.prisma.academicYear.create({
      data: {
        schoolId,
        name: data.name,
        startDate: new Date(data.startDate),
        endDate: new Date(data.endDate),
      },
      include: { terms: true },
    });
  }

  async setCurrentAcademicYear(schoolId: string, id: string) {
    await this.prisma.$transaction([
      this.prisma.academicYear.updateMany({
        where: { schoolId, isCurrent: true },
        data: { isCurrent: false },
      }),
      this.prisma.academicYear.update({
        where: { id },
        data: { isCurrent: true },
      }),
    ]);
    return { message: 'Current academic year updated' };
  }

  // ─── Terms ───────────────────────────────────────────────────────────────────
  async getTerms(schoolId: string, current?: boolean) {
    return this.prisma.term.findMany({
      where: {
        academicYear: { schoolId },
        ...(current !== undefined && { isCurrent: current }),
      },
      include: { academicYear: { select: { name: true } } },
      orderBy: { startDate: 'desc' },
    });
  }

  async createTerm(academicYearId: string, data: any) {
    return this.prisma.term.create({
      data: {
        academicYearId,
        name: data.name,
        type: data.type,
        startDate: new Date(data.startDate),
        endDate: new Date(data.endDate),
      },
    });
  }

  // ─── Roles ───────────────────────────────────────────────────────────────────
  async getRoles(schoolId: string) {
    return this.prisma.role.findMany({
      where: { OR: [{ schoolId }, { isSystem: true }] },
      include: {
        _count: { select: { users: true, permissions: true } },
      },
      orderBy: [{ isSystem: 'desc' }, { name: 'asc' }],
    });
  }

  async createRole(schoolId: string, data: any) {
    const slugify = (s: string) => s.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    return this.prisma.role.create({
      data: {
        schoolId,
        name: data.name,
        slug: slugify(data.name),
        description: data.description,
        color: data.color,
        isSystem: false,
      },
    });
  }

  // ─── Departments ─────────────────────────────────────────────────────────────
  async getDepartments(schoolId: string) {
    return this.prisma.department.findMany({
      where: { schoolId },
      include: {
        head: { include: { user: { select: { firstName: true, lastName: true } } } },
        _count: { select: { staff: true, subjects: true } },
      },
      orderBy: { name: 'asc' },
    });
  }

  async createDepartment(schoolId: string, data: any) {
    return this.prisma.department.create({
      data: { schoolId, name: data.name, code: data.code, description: data.description },
    });
  }
}
