import { Module } from '@nestjs/common';
import { Injectable } from '@nestjs/common';
import { Controller, Get, Put, Post, Delete, Patch, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class SettingsService {
  constructor(private readonly prisma: PrismaService) {}

  async getNotificationTemplates(schoolId: string) {
    return this.prisma.notificationTemplate.findMany({ where: { schoolId, isActive: true } });
  }

  async upsertTemplate(schoolId: string, data: any) {
    return this.prisma.notificationTemplate.upsert({
      where: { id: data.id || 'new' },
      create: { schoolId, name: data.name, type: data.type, subject: data.subject, body: data.body, variables: data.variables },
      update: { name: data.name, subject: data.subject, body: data.body, variables: data.variables },
    });
  }


  async getRoles(schoolId: string) {
    return this.prisma.role.findMany({
      where: { schoolId },
      include: { _count: { select: { users: true } }, permissions: true },
      orderBy: { createdAt: 'asc' },
    });
  }

  async getRole(id: string) {
    return this.prisma.role.findUnique({ where: { id }, include: { permissions: true } });
  }

  async createRole(schoolId: string, dto: { name: string; description?: string; permissions: string[] }) {
    return this.prisma.role.create({
      data: {
        schoolId,
        name: dto.name,
        description: dto.description,
        isSystem: false,
        permissions: {
          create: dto.permissions.map((p: string) => {
            const [module, resource, action] = p.split(':');
            return { module, resource, action };
          }),
        },
      },
      include: { permissions: true },
    });
  }

  async updateRole(id: string, dto: { name?: string; description?: string; permissions?: string[] }) {
    if (dto.permissions) {
      await this.prisma.permission.deleteMany({ where: { roleId: id } });
      await this.prisma.permission.createMany({
        data: dto.permissions.map((p: string) => {
          const [module, resource, action] = p.split(':');
          return { roleId: id, module, resource, action };
        }),
      });
    }
    return this.prisma.role.update({
      where: { id },
      data: { name: dto.name, description: dto.description },
      include: { permissions: true },
    });
  }

  async cloneRole(id: string, newName: string, schoolId: string) {
    const original = await this.prisma.role.findUnique({ where: { id }, include: { permissions: true } });
    if (!original) throw new Error('Role not found');
    return this.prisma.role.create({
      data: {
        schoolId,
        name: newName,
        description: `Cloned from ${original.name}`,
        isSystem: false,
        permissions: {
          create: original.permissions.map((p: any) => ({ module: p.module, resource: p.resource, action: p.action })),
        },
      },
      include: { permissions: true },
    });
  }

  async deleteRole(id: string) {
    const role = await this.prisma.role.findUnique({ where: { id } });
    if (role?.isSystem) throw new Error('Cannot delete system roles');
    return this.prisma.role.delete({ where: { id } });
  }

  async toggleRole(id: string, isActive: boolean) {
    return this.prisma.role.update({ where: { id }, data: { isActive } });
  }

  async assignRoleToUser(userId: string, roleId: string) {
    return this.prisma.userRole.upsert({
      where: { userId_roleId: { userId, roleId } },
      create: { userId, roleId },
      update: {},
    });
  }

  async getPermissionMatrix() {
    // Return all available permissions grouped by module
    return {
      students: ['students:students:READ', 'students:students:CREATE', 'students:students:UPDATE', 'students:students:DELETE'],
      teachers: ['teachers:teachers:READ', 'teachers:teachers:CREATE', 'teachers:teachers:UPDATE'],
      finance: ['finance:invoices:READ', 'finance:invoices:CREATE', 'finance:payments:READ', 'finance:payments:CREATE'],
      hr: ['hr:staff:READ', 'hr:staff:CREATE', 'hr:payroll:READ', 'hr:payroll:CREATE', 'hr:leave:READ', 'hr:leave:APPROVE'],
      results: ['results:results:READ', 'results:results:CREATE'],
      attendance: ['attendance:attendance:READ', 'attendance:attendance:CREATE'],
      admissions: ['admissions:admissions:READ', 'admissions:admissions:CREATE', 'admissions:admissions:UPDATE'],
      library: ['library:library:READ', 'library:library:CREATE'],
      ai: ['ai:ai:READ', 'ai:ai:CREATE'],
      reports: ['reports:reports:READ', 'reports:reports:EXPORT'],
      settings: ['settings:settings:READ', 'settings:settings:UPDATE', 'settings:roles:MANAGE'],
      audit: ['audit:audit:READ'],
      inventory: ['inventory:inventory:READ', 'inventory:inventory:CREATE', 'inventory:inventory:UPDATE'],
      clinic: ['clinic:clinic:READ', 'clinic:clinic:CREATE'],
      communications: ['communications:messages:READ', 'communications:messages:CREATE', 'communications:broadcasts:CREATE'],
      lms: ['lms:courses:READ', 'lms:courses:CREATE', 'lms:courses:UPDATE'],
    };
  }

  async getDepartments(schoolId: string) {
    return this.prisma.department.findMany({ where: { schoolId }, orderBy: { name: 'asc' } });
  }

  async createDepartment(schoolId: string, dto: { name: string; description?: string; headId?: string }) {
    return this.prisma.department.create({ data: { schoolId, ...dto } });
  }

  async updateDepartment(id: string, dto: any) {
    return this.prisma.department.update({ where: { id }, data: dto });
  }

  async deleteDepartment(id: string) {
    return this.prisma.department.delete({ where: { id } });
  }

  async getAcademicYears(schoolId: string) {
    return this.prisma.academicYear.findMany({ where: { schoolId }, orderBy: { startDate: 'desc' } });
  }

  async createAcademicYear(schoolId: string, dto: any) {
    return this.prisma.academicYear.create({ data: { schoolId, ...dto } });
  }

  async updateAcademicYear(id: string, dto: any) {
    return this.prisma.academicYear.update({ where: { id }, data: dto });
  }

  async getTerms(schoolId: string) {
    return this.prisma.term.findMany({ where: { academicYear: { schoolId } }, include: { academicYear: true }, orderBy: { startDate: 'desc' } });
  }

  async createTerm(dto: { academicYearId: string; name: string; startDate: string; endDate: string }) {
    return this.prisma.term.create({ data: { ...dto, startDate: new Date(dto.startDate), endDate: new Date(dto.endDate) } });
  }

  async getAuditLogs(schoolId: string, query: any = {}) {
    const { page = 1, limit = 50 } = query;
    const [data, total] = await Promise.all([
      this.prisma.auditLog.findMany({ where: { schoolId }, skip: (page-1)*limit, take: limit, include: { user: { select: { firstName: true, lastName: true, email: true } } }, orderBy: { createdAt: 'desc' } }),
      this.prisma.auditLog.count({ where: { schoolId } }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }
}

@ApiTags('Settings') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'settings', version: '1' })
export class SettingsController {
  constructor(private readonly service: SettingsService) {}

  @Get('roles') @RequirePermissions('settings:roles:MANAGE') getRoles(@SchoolId() sid: string) { return this.service.getRoles(sid); }
  @Get('roles/permissions-matrix') getMatrix() { return this.service.getPermissionMatrix(); }
  @Get('roles/:id') @RequirePermissions('settings:roles:MANAGE') getRole(@Param('id') id: string) { return this.service.getRole(id); }
  @Post('roles') @RequirePermissions('settings:roles:MANAGE') createRole(@SchoolId() sid: string, @Body() d: any) { return this.service.createRole(sid, d); }
  @Put('roles/:id') @RequirePermissions('settings:roles:MANAGE') updateRole(@Param('id') id: string, @Body() d: any) { return this.service.updateRole(id, d); }
  @Post('roles/:id/clone') @RequirePermissions('settings:roles:MANAGE') cloneRole(@Param('id') id: string, @SchoolId() sid: string, @Body() b: any) { return this.service.cloneRole(id, b.name, sid); }
  @Delete('roles/:id') @RequirePermissions('settings:roles:MANAGE') deleteRole(@Param('id') id: string) { return this.service.deleteRole(id); }
  @Patch('roles/:id/toggle') @RequirePermissions('settings:roles:MANAGE') toggleRole(@Param('id') id: string, @Body() b: any) { return this.service.toggleRole(id, b.isActive); }
  @Post('roles/assign') @RequirePermissions('settings:roles:MANAGE') assignRole(@Body() b: any) { return this.service.assignRoleToUser(b.userId, b.roleId); }

  @Get('departments') @RequirePermissions('settings:settings:READ') getDepts(@SchoolId() sid: string) { return this.service.getDepartments(sid); }
  @Post('departments') @RequirePermissions('settings:settings:UPDATE') createDept(@SchoolId() sid: string, @Body() d: any) { return this.service.createDepartment(sid, d); }
  @Put('departments/:id') @RequirePermissions('settings:settings:UPDATE') updateDept(@Param('id') id: string, @Body() d: any) { return this.service.updateDepartment(id, d); }
  @Delete('departments/:id') @RequirePermissions('settings:settings:UPDATE') deleteDept(@Param('id') id: string) { return this.service.deleteDepartment(id); }

  @Get('academic-years') @RequirePermissions('settings:settings:READ') getYears(@SchoolId() sid: string) { return this.service.getAcademicYears(sid); }
  @Post('academic-years') @RequirePermissions('settings:settings:UPDATE') createYear(@SchoolId() sid: string, @Body() d: any) { return this.service.createAcademicYear(sid, d); }
  @Put('academic-years/:id') @RequirePermissions('settings:settings:UPDATE') updateYear(@Param('id') id: string, @Body() d: any) { return this.service.updateAcademicYear(id, d); }

  @Get('terms') @RequirePermissions('settings:settings:READ') getTerms(@SchoolId() sid: string) { return this.service.getTerms(sid); }
  @Post('terms') @RequirePermissions('settings:settings:UPDATE') createTerm(@Body() d: any) { return this.service.createTerm(d); }

  @Get('notification-templates') @RequirePermissions('settings:settings:READ') getTemplates(@SchoolId() sid: string) { return this.service.getNotificationTemplates(sid); }
  @Put('notification-templates') @RequirePermissions('settings:settings:UPDATE') upsertTemplate(@SchoolId() sid: string, @Body() d: any) { return this.service.upsertTemplate(sid, d); }
  @Get('audit-logs') @RequirePermissions('settings:settings:READ') getAuditLogs(@SchoolId() sid: string) { return this.service.getAuditLogs(sid); }
}

@Module({ controllers: [SettingsController], providers: [SettingsService], exports: [SettingsService] })
export class SettingsModule {}
