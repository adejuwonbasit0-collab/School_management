import { Controller, Get, Patch, Param, Query, Req, UseGuards } from '@nestjs/common';
import { ParentPortalService } from './parent-portal.service';
import { JwtAuthGuard } from '../../guards/jwt-auth.guard';

@Controller('parent-portal')
@UseGuards(JwtAuthGuard)
export class ParentPortalController {
  constructor(private readonly parentPortalService: ParentPortalService) {}

  @Get('dashboard')
  getDashboard(@Req() req: any) {
    return this.parentPortalService.getDashboardSummary(req.user.id);
  }

  @Get('children')
  getChildren(@Req() req: any) {
    return this.parentPortalService.getChildren(req.user.id);
  }

  @Get('children/:studentId/attendance')
  getChildAttendance(
    @Req() req: any,
    @Param('studentId') studentId: string,
    @Query() query: any,
  ) {
    return this.parentPortalService.getChildAttendance(req.user.id, studentId, {
      termId: query.termId,
      month: query.month ? parseInt(query.month) : undefined,
      year: query.year ? parseInt(query.year) : undefined,
    });
  }

  @Get('children/:studentId/results')
  getChildResults(@Req() req: any, @Param('studentId') studentId: string) {
    return this.parentPortalService.getChildResults(req.user.id, studentId);
  }

  @Get('children/:studentId/invoices')
  getChildInvoices(@Req() req: any, @Param('studentId') studentId: string) {
    return this.parentPortalService.getChildInvoices(req.user.id, studentId);
  }

  @Get('notifications')
  getNotifications(@Req() req: any) {
    return this.parentPortalService.getParentNotifications(req.user.id);
  }

  @Patch('notifications/:id/read')
  markRead(@Req() req: any, @Param('id') id: string) {
    return this.parentPortalService.markNotificationRead(req.user.id, id);
  }
}
