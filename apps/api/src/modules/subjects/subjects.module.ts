import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class SubjectsService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(schoolId: string, query: any = {}) {
    const { page = 1, limit = 50, search, departmentId } = query;
    const where: any = { schoolId, isActive: true, ...(search && { name: { contains: search, mode: 'insensitive' } }), ...(departmentId && { departmentId }) };
    const [data, total] = await Promise.all([
      this.prisma.subject.findMany({ where, skip: (page-1)*limit, take: limit, include: { department: { select: { name: true } }, _count: { select: { classSubjects: true, teachers: true } } }, orderBy: { name: 'asc' } }),
      this.prisma.subject.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }

  async create(schoolId: string, data: any) {
    return this.prisma.subject.create({ data: { schoolId, name: data.name, code: data.code, description: data.description, departmentId: data.departmentId, isElective: data.isElective } });
  }

  async update(id: string, data: any) {
    return this.prisma.subject.update({ where: { id }, data: { name: data.name, code: data.code, description: data.description, departmentId: data.departmentId, isElective: data.isElective } });
  }

  async remove(id: string) {
    await this.prisma.subject.update({ where: { id }, data: { isActive: false } });
    return { message: 'Subject deactivated' };
  }
}

@ApiTags('Subjects') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'subjects', version: '1' })
export class SubjectsController {
  constructor(private readonly s: SubjectsService) {}
  @Get() @RequirePermissions('subjects:subjects:READ') findAll(@SchoolId() sid: string, @Query() q: any) { return this.s.findAll(sid, q); }
  @Post() @RequirePermissions('subjects:subjects:CREATE') create(@SchoolId() sid: string, @Body() d: any) { return this.s.create(sid, d); }
  @Put(':id') @RequirePermissions('subjects:subjects:UPDATE') update(@Param('id') id: string, @Body() d: any) { return this.s.update(id, d); }
  @Delete(':id') @RequirePermissions('subjects:subjects:DELETE') remove(@Param('id') id: string) { return this.s.remove(id); }
}

@Module({ controllers: [SubjectsController], providers: [SubjectsService], exports: [SubjectsService] })
export class SubjectsModule {}
