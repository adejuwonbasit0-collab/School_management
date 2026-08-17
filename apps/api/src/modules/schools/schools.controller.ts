import {
  Controller, Get, Post, Put, Body, Param, Query, UseGuards,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { SchoolsService } from './schools.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';

@ApiTags('Schools')
@ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'schools', version: '1' })
export class SchoolsController {
  constructor(private readonly schoolsService: SchoolsService) {}

  @Get('dashboard')
  @ApiOperation({ summary: 'Get school dashboard stats' })
  getDashboard(@SchoolId() schoolId: string) {
    return this.schoolsService.getDashboard(schoolId);
  }

  @Get('settings')
  @RequirePermissions('settings:settings:READ')
  getSettings(@SchoolId() schoolId: string) {
    return this.schoolsService.getSettings(schoolId);
  }

  @Put('settings')
  @RequirePermissions('settings:settings:UPDATE')
  updateSettings(@SchoolId() schoolId: string, @Body() data: any) {
    return this.schoolsService.updateSettings(schoolId, data);
  }

  // Academic Years
  @Get('academic-years')
  getAcademicYears(@SchoolId() schoolId: string) {
    return this.schoolsService.getAcademicYears(schoolId);
  }

  @Post('academic-years')
  @RequirePermissions('settings:settings:UPDATE')
  createAcademicYear(@SchoolId() schoolId: string, @Body() data: any) {
    return this.schoolsService.createAcademicYear(schoolId, data);
  }

  @Put('academic-years/:id/set-current')
  @RequirePermissions('settings:settings:UPDATE')
  setCurrentYear(@SchoolId() schoolId: string, @Param('id') id: string) {
    return this.schoolsService.setCurrentAcademicYear(schoolId, id);
  }

  // Terms
  @Get('terms')
  getTerms(@SchoolId() schoolId: string, @Query('current') current?: string) {
    return this.schoolsService.getTerms(schoolId, current === 'true' ? true : undefined);
  }

  @Post('academic-years/:id/terms')
  @RequirePermissions('settings:settings:UPDATE')
  createTerm(@Param('id') academicYearId: string, @Body() data: any) {
    return this.schoolsService.createTerm(academicYearId, data);
  }

  // Roles
  @Get('roles')
  getRoles(@SchoolId() schoolId: string) {
    return this.schoolsService.getRoles(schoolId);
  }

  @Post('roles')
  @RequirePermissions('settings:roles:CREATE')
  createRole(@SchoolId() schoolId: string, @Body() data: any) {
    return this.schoolsService.createRole(schoolId, data);
  }

  // Departments
  @Get('departments')
  getDepartments(@SchoolId() schoolId: string) {
    return this.schoolsService.getDepartments(schoolId);
  }

  @Post('departments')
  @RequirePermissions('settings:settings:UPDATE')
  createDepartment(@SchoolId() schoolId: string, @Body() data: any) {
    return this.schoolsService.createDepartment(schoolId, data);
  }
}
