import {
  Controller,
  Get,
  Post,
  Put,
  Patch,
  Delete,
  Body,
  Param,
  Query,
  UseGuards,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { StudentsService } from './students.service';
import { JwtAuthGuard } from '../../guards/jwt-auth.guard';
import { PermissionsGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, RequirePermissions, SchoolId, ApiPagination } from '../../decorators/current-user.decorator';
import {
  CreateStudentDto,
  UpdateStudentDto,
  EnrollStudentDto,
  StudentQueryDto,
  PromoteStudentsDto,
} from './dto';

@ApiTags('Students')
@ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'students', version: '1' })
export class StudentsController {
  constructor(private readonly studentsService: StudentsService) {}

  @Get()
  @ApiOperation({ summary: 'List all students' })
  @ApiPagination()
  @RequirePermissions('students:students:READ')
  findAll(@SchoolId() schoolId: string, @Query() query: StudentQueryDto) {
    return this.studentsService.findAll(schoolId, query);
  }

  @Get('stats')
  @ApiOperation({ summary: 'Get student statistics' })
  @RequirePermissions('students:students:READ')
  getStats(@SchoolId() schoolId: string) {
    return this.studentsService.getStats(schoolId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get student by ID' })
  @RequirePermissions('students:students:READ')
  findOne(@SchoolId() schoolId: string, @Param('id') id: string) {
    return this.studentsService.findOne(schoolId, id);
  }

  @Post()
  @ApiOperation({ summary: 'Create new student' })
  @RequirePermissions('students:students:CREATE')
  create(
    @SchoolId() schoolId: string,
    @Body() dto: CreateStudentDto,
    @CurrentUser('id') userId: string,
  ) {
    return this.studentsService.create(schoolId, dto, userId);
  }

  @Put(':id')
  @ApiOperation({ summary: 'Update student' })
  @RequirePermissions('students:students:UPDATE')
  update(
    @SchoolId() schoolId: string,
    @Param('id') id: string,
    @Body() dto: UpdateStudentDto,
  ) {
    return this.studentsService.update(schoolId, id, dto);
  }

  @Post(':id/enroll')
  @ApiOperation({ summary: 'Enroll student in a class' })
  @RequirePermissions('students:students:UPDATE')
  enroll(
    @SchoolId() schoolId: string,
    @Param('id') id: string,
    @Body() dto: EnrollStudentDto,
  ) {
    return this.studentsService.enroll(schoolId, id, dto);
  }

  @Post('promote')
  @ApiOperation({ summary: 'Promote students to next class' })
  @RequirePermissions('students:students:MANAGE')
  promote(@SchoolId() schoolId: string, @Body() dto: PromoteStudentsDto) {
    return this.studentsService.promoteStudents(
      schoolId,
      dto.fromClassId,
      dto.toClassId,
      dto.academicYearId,
      dto.studentIds,
    );
  }

  @Get(':id/attendance/:termId')
  @ApiOperation({ summary: 'Get student attendance summary' })
  @RequirePermissions('students:students:READ')
  getAttendance(
    @SchoolId() schoolId: string,
    @Param('id') id: string,
    @Param('termId') termId: string,
  ) {
    return this.studentsService.getAttendanceSummary(schoolId, id, termId);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Archive student' })
  @RequirePermissions('students:students:DELETE')
  @HttpCode(HttpStatus.OK)
  remove(@SchoolId() schoolId: string, @Param('id') id: string) {
    return this.studentsService.remove(schoolId, id);
  }
}
