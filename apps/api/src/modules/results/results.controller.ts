import {
  Controller, Get, Post, Put, Delete, Patch, Body, Param, Query, Req, Res, UseGuards, HttpCode
} from '@nestjs/common';
import { Response } from 'express';
import { ResultsService } from './results.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';

@Controller('results')
@UseGuards(JwtAuthGuard, PermissionsGuard)
export class ResultsController {
  constructor(private readonly resultsService: ResultsService) {}

  // ── Grade Scales ───────────────────────────────────────────────────────

  @Get('grade-scales') @RequirePermissions('results:results:READ')
  getGradeScales(@Req() req: any) {
    return this.resultsService.getGradeScales(req.user.schoolId);
  }

  @Post('grade-scales') @RequirePermissions('results:results:CREATE')
  createGradeScale(@Req() req: any, @Body() dto: any) {
    return this.resultsService.createGradeScale(req.user.schoolId, dto);
  }

  @Put('grade-scales/:id') @RequirePermissions('results:results:UPDATE')
  updateGradeScale(@Param('id') id: string, @Req() req: any, @Body() dto: any) {
    return this.resultsService.updateGradeScale(id, req.user.schoolId, dto);
  }

  @Delete('grade-scales/:id') @RequirePermissions('results:results:DELETE')
  deleteGradeScale(@Param('id') id: string, @Req() req: any) {
    return this.resultsService.deleteGradeScale(id, req.user.schoolId);
  }

  // ── Result Config ──────────────────────────────────────────────────────

  @Get('config') @RequirePermissions('results:results:READ')
  getConfig(@Req() req: any) {
    return this.resultsService.getResultConfig(req.user.schoolId);
  }

  @Put('config') @RequirePermissions('results:results:UPDATE')
  updateConfig(@Req() req: any, @Body() dto: any) {
    return this.resultsService.upsertResultConfig(req.user.schoolId, dto);
  }

  // ── Score Entry ────────────────────────────────────────────────────────

  @Post('examinations/:examId/results/:studentId') @RequirePermissions('results:results:CREATE')
  upsertResult(
    @Param('examId') examId: string,
    @Param('studentId') studentId: string,
    @Body() body: { scores: Record<string, any>; remarks?: string },
  ) {
    return this.resultsService.upsertExamResult(examId, studentId, body.scores, { remarks: body.remarks });
  }

  @Get('examinations/:examId/results') @RequirePermissions('results:results:READ')
  getExamResults(@Param('examId') examId: string) {
    return this.resultsService.getExamResults(examId);
  }

  @Post('examinations/:examId/compute-positions') @RequirePermissions('results:results:UPDATE')
  @HttpCode(200)
  computePositions(@Param('examId') examId: string) {
    return this.resultsService.computePositions(examId);
  }

  @Post('examinations/:examId/publish') @RequirePermissions('results:results:UPDATE')
  @HttpCode(200)
  publishResults(@Param('examId') examId: string, @Req() req: any) {
    return this.resultsService.publishResults(examId, req.user.id);
  }

  // ── Broadsheet ─────────────────────────────────────────────────────────

  @Get('examinations/:examId/broadsheet') @RequirePermissions('results:results:READ')
  getBroadsheet(@Param('examId') examId: string, @Query('classRoomId') classRoomId: string) {
    return this.resultsService.getBroadsheet(examId, classRoomId);
  }

  // ── Report Card PDF ────────────────────────────────────────────────────

  @Get('examinations/:examId/students/:studentId/report-card')
  async getReportCard(
    @Param('examId') examId: string,
    @Param('studentId') studentId: string,
    @Res() res: Response,
  ) {
    const buffer = await this.resultsService.generateReportCard(examId, studentId);
    res.set({
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="report-card-${studentId}.pdf"`,
      'Content-Length': buffer.length,
    });
    res.end(buffer);
  }

  // ── Student Results History ────────────────────────────────────────────

  @Get('students/:studentId')
  getStudentResults(@Param('studentId') studentId: string, @Query('termId') termId?: string) {
    return this.resultsService.getStudentResults(studentId, termId);
  }
}
