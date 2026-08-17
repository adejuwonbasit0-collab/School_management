import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';

@Injectable()
export class TimetableService {
  constructor(private prisma: PrismaService) {}

  async getClassTimetable(classRoomId: string) {
    return this.prisma.timetable.findMany({
      where: { classRoomId, isActive: true },
      include: {
        subject: true,
        classRoom: true,
      },
      orderBy: [{ dayOfWeek: 'asc' }, { startTime: 'asc' }],
    });
  }

  async getMyTimetable(userId: string) {
    const teacher = await this.prisma.teacher.findFirst({ where: { staff: { userId } } });
    if (!teacher) return [];
    return this.getTeacherTimetable(teacher.id);
  }

  async getTeacherTimetable(teacherId: string) {
    const subjects = await this.prisma.teacherSubject.findMany({
      where: { teacherId },
      select: { subjectId: true },
    });
    const subjectIds = subjects.map(s => s.subjectId);

    return this.prisma.timetable.findMany({
      where: { subjectId: { in: subjectIds }, isActive: true },
      include: { subject: true, classRoom: true },
      orderBy: [{ dayOfWeek: 'asc' }, { startTime: 'asc' }],
    });
  }

  async createSlot(schoolId: string, dto: {
    classRoomId: string;
    subjectId: string;
    teacherId?: string;
    dayOfWeek: number;
    startTime: string;
    endTime: string;
    room?: string;
  }) {
    // Validate class belongs to school
    const classRoom = await this.prisma.classRoom.findFirst({
      where: { id: dto.classRoomId, schoolId },
    });
    if (!classRoom) throw new NotFoundException('Class not found');

    // Conflict: same class, same day, overlapping time
    const classConflict = await this.checkTimeConflict(
      dto.classRoomId, null, dto.dayOfWeek, dto.startTime, dto.endTime
    );
    if (classConflict) {
      throw new ConflictException(`Time conflict: this class already has a subject at ${dto.startTime}–${dto.endTime} on day ${dto.dayOfWeek}`);
    }

    // Conflict: same teacher, same day, overlapping time
    if (dto.teacherId) {
      const teacherSlots = await this.getTeacherTimetable(dto.teacherId);
      const teacherConflict = teacherSlots.find(slot =>
        slot.dayOfWeek === dto.dayOfWeek &&
        this.timesOverlap(slot.startTime, slot.endTime, dto.startTime, dto.endTime)
      );
      if (teacherConflict) {
        throw new ConflictException(`Teacher conflict: teacher already assigned at ${dto.startTime}–${dto.endTime} on day ${dto.dayOfWeek}`);
      }
    }

    return this.prisma.timetable.create({ data: dto, include: { subject: true, classRoom: true } });
  }

  async updateSlot(id: string, schoolId: string, dto: {
    subjectId?: string;
    teacherId?: string;
    dayOfWeek?: number;
    startTime?: string;
    endTime?: string;
    room?: string;
  }) {
    const slot = await this.prisma.timetable.findFirst({
      where: { id },
      include: { classRoom: true },
    });
    if (!slot || slot.classRoom.schoolId !== schoolId) throw new NotFoundException('Slot not found');

    const day = dto.dayOfWeek ?? slot.dayOfWeek;
    const start = dto.startTime ?? slot.startTime;
    const end = dto.endTime ?? slot.endTime;

    // Conflict check excluding current slot
    const classConflict = await this.checkTimeConflict(slot.classRoomId, id, day, start, end);
    if (classConflict) {
      throw new ConflictException(`Time conflict with another slot`);
    }

    return this.prisma.timetable.update({
      where: { id },
      data: dto,
      include: { subject: true, classRoom: true },
    });
  }

  async deleteSlot(id: string, schoolId: string) {
    const slot = await this.prisma.timetable.findFirst({
      where: { id },
      include: { classRoom: true },
    });
    if (!slot || slot.classRoom.schoolId !== schoolId) throw new NotFoundException('Slot not found');
    return this.prisma.timetable.delete({ where: { id } });
  }

  async getAllClassesTimetable(schoolId: string) {
    const classes = await this.prisma.classRoom.findMany({
      where: { schoolId, isActive: true },
      select: { id: true, name: true, section: true },
    });
    return classes;
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  private async checkTimeConflict(
    classRoomId: string,
    excludeId: string | null,
    dayOfWeek: number,
    startTime: string,
    endTime: string,
  ) {
    const existing = await this.prisma.timetable.findMany({
      where: {
        classRoomId,
        dayOfWeek,
        isActive: true,
        ...(excludeId ? { NOT: { id: excludeId } } : {}),
      },
    });
    return existing.some(s => this.timesOverlap(s.startTime, s.endTime, startTime, endTime));
  }

  private timesOverlap(s1: string, e1: string, s2: string, e2: string): boolean {
    const toMin = (t: string) => {
      const [h, m] = t.split(':').map(Number);
      return h * 60 + m;
    };
    return toMin(s2) < toMin(e1) && toMin(s1) < toMin(e2);
  }
}
