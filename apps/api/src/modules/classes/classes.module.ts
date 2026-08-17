// Classes module
import { Module } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class ClassesService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(schoolId: string, query: any = {}) {
    const { page = 1, limit = 50, search } = query;
    const where: any = {
      schoolId,
      isActive: true,
      ...(search && { name: { contains: search, mode: 'insensitive' } }),
    };
    const [data, total] = await Promise.all([
      this.prisma.classRoom.findMany({
        where, skip: (page - 1) * limit, take: limit,
        include: {
          classTeacher: { include: { staff: { include: { user: { select: { firstName: true, lastName: true } } } } } },
          _count: { select: { enrollments: true, subjects: true } },
        },
        orderBy: [{ level: 'asc' }, { name: 'asc' }],
      }),
      this.prisma.classRoom.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total / limit) } };
  }

  async findOne(schoolId: string, id: string) {
    const cls = await this.prisma.classRoom.findFirst({
      where: { id, schoolId },
      include: {
        classTeacher: { include: { staff: { include: { user: { select: { firstName: true, lastName: true, avatar: true } } } } } },
        subjects: { include: { subject: true, teacher: { include: { staff: { include: { user: { select: { firstName: true, lastName: true } } } } } } } },
        enrollments: {
          where: { isCurrent: true },
          include: { student: { include: { user: { select: { firstName: true, lastName: true, avatar: true, gender: true } } } } },
          orderBy: { rollNumber: 'asc' },
        },
        timetable: { include: { subject: true }, orderBy: [{ dayOfWeek: 'asc' }, { startTime: 'asc' }] },
      },
    });
    if (!cls) throw new NotFoundException('Class not found');
    return cls;
  }

  async create(schoolId: string, data: any) {
    return this.prisma.classRoom.create({
      data: { schoolId, name: data.name, section: data.section, level: data.level, capacity: data.capacity || 30, room: data.room },
    });
  }

  async update(schoolId: string, id: string, data: any) {
    return this.prisma.classRoom.update({
      where: { id },
      data: { name: data.name, section: data.section, level: data.level, capacity: data.capacity, classTeacherId: data.classTeacherId, room: data.room },
    });
  }

  async assignSubject(classRoomId: string, data: any) {
    return this.prisma.classSubject.upsert({
      where: { classRoomId_subjectId: { classRoomId, subjectId: data.subjectId } },
      create: { classRoomId, subjectId: data.subjectId, teacherId: data.teacherId },
      update: { teacherId: data.teacherId },
    });
  }

  async addTimetableEntry(classRoomId: string, data: any) {
    return this.prisma.timetable.create({
      data: { classRoomId, subjectId: data.subjectId, dayOfWeek: data.dayOfWeek, startTime: data.startTime, endTime: data.endTime, room: data.room },
    });
  }
}

@ApiTags('Classes')
@ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'classes', version: '1' })
export class ClassesController {
  constructor(private readonly classesService: ClassesService) {}

  @Get() @RequirePermissions('classes:classes:READ')
  findAll(@SchoolId() schoolId: string, @Query() query: any) { return this.classesService.findAll(schoolId, query); }

  @Get(':id') @RequirePermissions('classes:classes:READ')
  findOne(@SchoolId() schoolId: string, @Param('id') id: string) { return this.classesService.findOne(schoolId, id); }

  @Post() @RequirePermissions('classes:classes:CREATE')
  create(@SchoolId() schoolId: string, @Body() data: any) { return this.classesService.create(schoolId, data); }

  @Put(':id') @RequirePermissions('classes:classes:UPDATE')
  update(@SchoolId() schoolId: string, @Param('id') id: string, @Body() data: any) { return this.classesService.update(schoolId, id, data); }

  @Post(':id/subjects') @RequirePermissions('classes:classes:UPDATE')
  assignSubject(@Param('id') id: string, @Body() data: any) { return this.classesService.assignSubject(id, data); }

  @Post(':id/timetable') @RequirePermissions('classes:classes:UPDATE')
  addTimetable(@Param('id') id: string, @Body() data: any) { return this.classesService.addTimetableEntry(id, data); }
}

@Module({
  controllers: [ClassesController],
  providers: [ClassesService],
  exports: [ClassesService],
})
export class ClassesModule {}
