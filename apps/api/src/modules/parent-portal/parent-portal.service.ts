import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';

@Injectable()
export class ParentPortalService {
  constructor(private prisma: PrismaService) {}

  async getParentByUserId(userId: string) {
    const parent = await this.prisma.parent.findUnique({
      where: { userId },
      include: {
        children: {
          include: {
            student: {
              include: {
                user: { select: { firstName: true, lastName: true, avatar: true } },
                enrollments: {
                  where: { isCurrent: true },
                  include: { classRoom: true, academicYear: true },
                },
              },
            },
          },
        },
      },
    });
    if (!parent) throw new NotFoundException('Parent profile not found');
    return parent;
  }

  async getChildren(userId: string) {
    const parent = await this.prisma.parent.findUnique({ where: { userId } });
    if (!parent) throw new NotFoundException('Parent not found');

    const links = await this.prisma.studentParent.findMany({
      where: { parentId: parent.id },
      include: {
        student: {
          include: {
            user: { select: { firstName: true, lastName: true, avatar: true, email: true } },
            school: { select: { name: true, logo: true } },
            enrollments: {
              where: { isCurrent: true },
              include: { classRoom: true, academicYear: true },
            },
          },
        },
      },
    });

    return links.map(l => ({
      ...l.student,
      relationship: l.relationship,
      isPrimary: l.isPrimary,
    }));
  }

  private async verifyParentHasChild(userId: string, studentId: string) {
    const parent = await this.prisma.parent.findUnique({ where: { userId } });
    if (!parent) throw new NotFoundException('Parent not found');

    const link = await this.prisma.studentParent.findFirst({
      where: { parentId: parent.id, studentId },
    });
    if (!link) throw new ForbiddenException('You do not have access to this student');
    return parent;
  }

  async getChildAttendance(userId: string, studentId: string, query: {
    termId?: string; month?: number; year?: number;
  }) {
    await this.verifyParentHasChild(userId, studentId);

    const where: any = { studentId };
    if (query.termId) where.termId = query.termId;
    if (query.month && query.year) {
      const start = new Date(query.year, query.month - 1, 1);
      const end = new Date(query.year, query.month, 0, 23, 59, 59);
      where.date = { gte: start, lte: end };
    }

    const records = await this.prisma.attendance.findMany({
      where,
      include: { classRoom: true },
      orderBy: { date: 'desc' },
    });

    const summary = {
      total: records.length,
      present: records.filter(r => r.status === 'PRESENT').length,
      absent: records.filter(r => r.status === 'ABSENT').length,
      late: records.filter(r => r.status === 'LATE').length,
      excused: records.filter(r => r.status === 'EXCUSED').length,
    };

    return { records, summary };
  }

  async getChildResults(userId: string, studentId: string) {
    await this.verifyParentHasChild(userId, studentId);

    return this.prisma.examResult.findMany({
      where: {
        studentId,
        publishedAt: { not: null },
      },
      include: {
        examination: {
          include: { term: true, academicYear: true },
        },
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  async getChildInvoices(userId: string, studentId: string) {
    await this.verifyParentHasChild(userId, studentId);

    return this.prisma.feeInvoice.findMany({
      where: { studentId },
      include: {
        items: true,
        payments: { orderBy: { createdAt: 'desc' } },
        term: true,
        feeStructure: true,
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  async getDashboardSummary(userId: string) {
    const parent = await this.prisma.parent.findUnique({ where: { userId } });
    if (!parent) throw new NotFoundException('Parent not found');

    const links = await this.prisma.studentParent.findMany({
      where: { parentId: parent.id },
      include: { student: { include: { user: true } } },
    });

    const studentIds = links.map(l => l.studentId);

    const [totalAbsent, pendingInvoices, recentResults] = await Promise.all([
      this.prisma.attendance.count({
        where: {
          studentId: { in: studentIds },
          status: 'ABSENT',
          date: { gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) },
        },
      }),
      this.prisma.feeInvoice.count({
        where: {
          studentId: { in: studentIds },
          status: { in: ['UNPAID', 'PARTIAL', 'OVERDUE'] },
        },
      }),
      this.prisma.examResult.findMany({
        where: {
          studentId: { in: studentIds },
          publishedAt: { not: null },
        },
        include: {
          examination: true,
          student: { include: { user: { select: { firstName: true, lastName: true } } } },
        },
        orderBy: { publishedAt: 'desc' },
        take: 5,
      }),
    ]);

    return {
      children: links.map(l => ({
        id: l.studentId,
        name: `${l.student.user?.firstName} ${l.student.user?.lastName}`,
        relationship: l.relationship,
      })),
      absentLast30Days: totalAbsent,
      pendingInvoices,
      recentResults,
    };
  }

  async getParentNotifications(userId: string) {
    const parent = await this.prisma.parent.findUnique({ where: { userId } });
    if (!parent) throw new NotFoundException('Parent not found');

    return this.prisma.parentNotification.findMany({
      where: { parentId: parent.id },
      orderBy: { createdAt: 'desc' },
      take: 50,
    });
  }

  async markNotificationRead(userId: string, notificationId: string) {
    const parent = await this.prisma.parent.findUnique({ where: { userId } });
    if (!parent) throw new NotFoundException('Parent not found');

    return this.prisma.parentNotification.update({
      where: { id: notificationId },
      data: { isRead: true, readAt: new Date() },
    });
  }
}
