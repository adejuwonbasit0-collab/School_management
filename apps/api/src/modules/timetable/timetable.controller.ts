import { Controller, Get, Post, Put, Delete, Body, Param, Query, Req, UseGuards } from '@nestjs/common';
import { TimetableService } from './timetable.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';

@Controller('timetable')
@UseGuards(JwtAuthGuard, PermissionsGuard)
export class TimetableController {
  constructor(private readonly timetableService: TimetableService) {}

  @Get('classes') @RequirePermissions('timetable:timetable:READ')
  getClasses(@Req() req: any) {
    return this.timetableService.getAllClassesTimetable(req.user.schoolId);
  }

  @Get('class/:classRoomId') @RequirePermissions('timetable:timetable:READ')
  getClassTimetable(@Param('classRoomId') classRoomId: string) {
    return this.timetableService.getClassTimetable(classRoomId);
  }

  @Get('teacher/me') @RequirePermissions('timetable:timetable:READ')
  getMyTimetable(@Req() req: any) {
    return this.timetableService.getMyTimetable(req.user.id);
  }

  @Get('teacher/:teacherId') @RequirePermissions('timetable:timetable:READ')
  getTeacherTimetable(@Param('teacherId') teacherId: string) {
    return this.timetableService.getTeacherTimetable(teacherId);
  }

  @Post('slots') @RequirePermissions('timetable:timetable:CREATE')
  createSlot(@Req() req: any, @Body() dto: any) {
    return this.timetableService.createSlot(req.user.schoolId, dto);
  }

  @Put('slots/:id') @RequirePermissions('timetable:timetable:UPDATE')
  updateSlot(@Param('id') id: string, @Req() req: any, @Body() dto: any) {
    return this.timetableService.updateSlot(id, req.user.schoolId, dto);
  }

  @Delete('slots/:id') @RequirePermissions('timetable:timetable:DELETE')
  deleteSlot(@Param('id') id: string, @Req() req: any) {
    return this.timetableService.deleteSlot(id, req.user.schoolId);
  }
}
