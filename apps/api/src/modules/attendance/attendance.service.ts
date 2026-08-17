import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { EventEmitter2 } from '@nestjs/event-emitter';
import { AttendanceStatus } from '@prisma/client';

@Injectable()
export class AttendanceService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  async markAttendance(schoolId: string, data: {
    classRoomId: string;
    termId: string;
    date: string;
    takenById: string;
    records: Array<{ studentId: string; status: AttendanceStatus; remarks?: string }>;
  }) {
    const classRoom = await this.prisma.classRoom.findFirst({
      where: { id: data.classRoomId, schoolId },
    });
    if (!classRoom) throw new NotFoundException('Class not found');

    const date = new Date(data.date);
    date.setHours(0, 0, 0, 0);

    // Upsert all records
    const results = await this.prisma.$transaction(
      data.records.map((record) =>
        this.prisma.attendance.upsert({
          where: {
            studentId_classRoomId_date: {
              studentId: record.studentId,
              classRoomId: data.classRoomId,
              date,
            },
          },
          create: {
            schoolId,
            studentId: record.studentId,
            classRoomId: data.classRoomId,
            termId: data.termId,
            takenById: data.takenById,
            date,
            status: record.status,
            remarks: record.remarks,
          },
          update: {
            status: record.status,
            remarks: record.remarks,
            takenById: data.takenById,
          },
        }),
      ),
    );

    // Fire events for absent students
    const absentStudents = data.records.filter((r) => r.status === 'ABSENT');
    if (absentStudents.length > 0) {
      this.eventEmitter.emit('attendance.absent', {
        schoolId,
        classRoomId: data.classRoomId,
        date: data.date,
        studentIds: absentStudents.map((r) => r.studentId),
      });
    }

    return { marked: results.length };
  }

  async getClassAttendance(schoolId: string, classRoomId: string, date: string) {
    const targetDate = new Date(date);
    targetDate.setHours(0, 0, 0, 0);

    const enrollments = await this.prisma.studentEnrollment.findMany({
      where: { classRoomId, isCurrent: true, student: { schoolId } },
      include: {
        student: {
          include: {
            user: { select: { id: true, firstName: true, lastName: true, avatar: true } },
            attendance: {
              where: { classRoomId, date: targetDate },
              take: 1,
            },
          },
        },
      },
      orderBy: { rollNumber: 'asc' },
    });

    return enrollments.map((e) => ({
      studentId: e.student.id,
      rollNumber: e.rollNumber,
      name: `${e.student.user.firstName} ${e.student.user.lastName}`,
      avatar: e.student.user.avatar,
      attendance: e.student.attendance[0] || null,
      status: e.student.attendance[0]?.status || null,
    }));
  }

  async getAttendanceReport(schoolId: string, query: {
    classRoomId?: string;
    studentId?: string;
    termId: string;
    startDate?: string;
    endDate?: string;
  }) {
    const where: any = {
      schoolId,
      termId: query.termId,
      ...(query.classRoomId && { classRoomId: query.classRoomId }),
      ...(query.studentId && { studentId: query.studentId }),
      ...(query.startDate && query.endDate && {
        date: { gte: new Date(query.startDate), lte: new Date(query.endDate) },
      }),
    };

    const records = await this.prisma.attendance.findMany({
      where,
      include: {
        student: {
          include: {
            user: { select: { firstName: true, lastName: true } },
          },
        },
      },
      orderBy: [{ date: 'desc' }, { student: { user: { firstName: 'asc' } } }],
    });

    // Aggregate by student
    const byStudent = records.reduce((acc, r) => {
      const key = r.studentId;
      if (!acc[key]) {
        acc[key] = {
          studentId: key,
          name: `${r.student.user.firstName} ${r.student.user.lastName}`,
          total: 0,
          present: 0,
          absent: 0,
          late: 0,
          excused: 0,
        };
      }
      acc[key].total++;
      const status = r.status.toLowerCase();
      if (acc[key][status] !== undefined) acc[key][status]++;
      return acc;
    }, {} as Record<string, any>);

    return {
      records,
      summary: Object.values(byStudent).map((s: any) => ({
        ...s,
        percentage: s.total > 0 ? Math.round(((s.present + s.late) / s.total) * 100) : 0,
      })),
    };
  }

  async getAttendanceTrend(schoolId: string, classRoomId: string, termId: string) {
    const records = await this.prisma.attendance.groupBy({
      by: ['date', 'status'],
      where: { schoolId, classRoomId, termId },
      _count: true,
      orderBy: { date: 'asc' },
    });

    const byDate = records.reduce((acc, r) => {
      const dateKey = r.date.toISOString().split('T')[0];
      if (!acc[dateKey]) acc[dateKey] = { date: dateKey, present: 0, absent: 0, late: 0 };
      const status = r.status.toLowerCase();
      if (acc[dateKey][status] !== undefined) acc[dateKey][status] = r._count;
      return acc;
    }, {} as Record<string, any>);

    return Object.values(byDate);
  }
}
