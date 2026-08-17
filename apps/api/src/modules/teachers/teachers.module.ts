import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class TeachersService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20, search } = query;
    const where: any = { staff: { schoolId, employmentStatus: 'ACTIVE' }, ...(search && { staff: { schoolId, OR: [{ user: { firstName: { contains: search, mode: 'insensitive' } } }, { user: { lastName: { contains: search, mode: 'insensitive' } } }] } }) };
    const [data, total] = await Promise.all([
      this.prisma.teacher.findMany({ where, skip: (page-1)*limit, take: limit, include: { staff: { include: { user: { select: { id: true, firstName: true, lastName: true, email: true, avatar: true } }, department: { select: { name: true } } } }, subjects: { include: { subject: { select: { name: true } } } }, classRooms: { select: { id: true, name: true, section: true } } }, }),
      this.prisma.teacher.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }

  async assignSubject(teacherId: string, subjectId: string) {
    return this.prisma.teacherSubject.upsert({
      where: { teacherId_subjectId: { teacherId, subjectId } },
      create: { teacherId, subjectId },
      update: {},
    });
  }

  async getTeacherClasses(teacherId: string) {
    return this.prisma.classSubject.findMany({
      where: { teacherId },
      include: { classRoom: { select: { name: true, section: true } }, subject: { select: { name: true } } },
    });
  }

  async getTeacherByUserId(userId: string) {
    return this.prisma.teacher.findFirst({
      where: { staff: { userId } },
      include: {
        staff: { include: { user: true, department: true } },
        subjects: { include: { subject: true } },
        classRooms: true,
      },
    });
  }
}

@ApiTags('Teachers') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'teachers', version: '1' })
export class TeachersController {
  constructor(private readonly service: TeachersService) {}
  @Get() @RequirePermissions('teachers:teachers:READ') findAll(@SchoolId() sid: string, @Query() q: any) { return this.service.findAll(sid, q); }
  @Post(':id/subjects') @RequirePermissions('teachers:teachers:UPDATE') assignSubject(@Param('id') id: string, @Body() body: any) { return this.service.assignSubject(id, body.subjectId); }

  @Get('my-profile') getMyProfile(@CurrentUser('id') uid: string) {
    return this.service.getTeacherByUserId(uid);
  }

  @Get(':id/classes') @RequirePermissions('teachers:teachers:READ') getClasses(@Param('id') id: string) { return this.service.getTeacherClasses(id); }
}

@Module({ controllers: [TeachersController], providers: [TeachersService], exports: [TeachersService] })
export class TeachersModule {}
