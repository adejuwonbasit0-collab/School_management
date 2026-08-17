import {
  Controller, Get, Post, Body, Param, Query, UseGuards,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { AttendanceService } from './attendance.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';

@ApiTags('Attendance')
@ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'attendance', version: '1' })
export class AttendanceController {
  constructor(private readonly attendanceService: AttendanceService) {}

  @Post()
  @RequirePermissions('attendance:attendance:CREATE')
  markAttendance(
    @SchoolId() schoolId: string,
    @CurrentUser() user: any,
    @Body() body: any,
  ) {
    return this.attendanceService.markAttendance(schoolId, {
      ...body,
      takenById: user.staff?.teacher?.id || user.id,
    });
  }

  @Get('class/:classRoomId')
  @RequirePermissions('attendance:attendance:READ')
  getClassAttendance(
    @SchoolId() schoolId: string,
    @Param('classRoomId') classRoomId: string,
    @Query('date') date: string,
  ) {
    return this.attendanceService.getClassAttendance(
      schoolId,
      classRoomId,
      date || new Date().toISOString().split('T')[0],
    );
  }

  @Get('report')
  @RequirePermissions('attendance:attendance:READ')
  getReport(@SchoolId() schoolId: string, @Query() query: any) {
    return this.attendanceService.getAttendanceReport(schoolId, query);
  }

  @Get('trend')
  @RequirePermissions('attendance:attendance:READ')
  getTrend(
    @SchoolId() schoolId: string,
    @Query('classRoomId') classRoomId: string,
    @Query('termId') termId: string,
  ) {
    return this.attendanceService.getAttendanceTrend(schoolId, classRoomId, termId);
  }
}
