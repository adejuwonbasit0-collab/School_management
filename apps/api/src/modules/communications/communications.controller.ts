import { Controller, Get, Post, Put, Delete, Patch, Body, Param, Query, Req, HttpCode, UseGuards } from '@nestjs/common';
import { CommunicationsService } from './communications.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';

@Controller('communications')
@UseGuards(JwtAuthGuard)
export class CommunicationsController {
  constructor(private readonly communicationsService: CommunicationsService) {}

  // ── Broadcasts ─────────────────────────────────────────────────────────

  @Get('broadcasts')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:broadcasts:READ')
  getBroadcasts(@Req() req: any, @Query() query: any) {
    return this.communicationsService.getBroadcasts(req.user.schoolId, query);
  }

  @Post('broadcasts')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:broadcasts:CREATE')
  createBroadcast(@Req() req: any, @Body() dto: any) {
    return this.communicationsService.createBroadcast(req.user.schoolId, req.user.id, dto);
  }

  @Post('broadcasts/:id/send')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:broadcasts:CREATE')
  @HttpCode(200)
  sendBroadcast(@Param('id') id: string, @Req() req: any) {
    return this.communicationsService.sendBroadcast(id, req.user.schoolId);
  }

  @Delete('broadcasts/:id')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:broadcasts:DELETE')
  deleteBroadcast(@Param('id') id: string, @Req() req: any) {
    return this.communicationsService.deleteBroadcast(id, req.user.schoolId);
  }

  // ── Templates ──────────────────────────────────────────────────────────

  @Get('templates')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:messages:MANAGE')
  getTemplates(@Req() req: any) {
    return this.communicationsService.getTemplates(req.user.schoolId);
  }

  @Post('templates')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:messages:MANAGE')
  createTemplate(@Req() req: any, @Body() dto: any) {
    return this.communicationsService.createTemplate(req.user.schoolId, dto);
  }

  @Put('templates/:id')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:messages:MANAGE')
  updateTemplate(@Param('id') id: string, @Req() req: any, @Body() dto: any) {
    return this.communicationsService.updateTemplate(id, req.user.schoolId, dto);
  }

  @Delete('templates/:id')
  @UseGuards(PermissionsGuard) @RequirePermissions('communications:messages:MANAGE')
  deleteTemplate(@Param('id') id: string, @Req() req: any) {
    return this.communicationsService.deleteTemplate(id, req.user.schoolId);
  }

  // ── Messages ────────────────────────────────────────────────────────────

  @Get('messages/inbox')
  getInbox(@Req() req: any, @Query() q: any) {
    return this.communicationsService.getMessages(req.user.id, 'inbox', +q.page || 1, +q.limit || 20);
  }

  @Get('messages/sent')
  getSent(@Req() req: any, @Query() q: any) {
    return this.communicationsService.getMessages(req.user.id, 'sent', +q.page || 1, +q.limit || 20);
  }

  @Get('messages/unread-count')
  getUnreadCount(@Req() req: any) {
    return this.communicationsService.getUnreadCount(req.user.id);
  }

  @Get('messages/:id')
  getMessage(@Param('id') id: string, @Req() req: any) {
    return this.communicationsService.getMessage(id, req.user.id);
  }

  @Post('messages')
  sendMessage(@Req() req: any, @Body() dto: any) {
    return this.communicationsService.sendMessage(req.user.id, dto);
  }

  @Delete('messages/:id')
  deleteMessage(@Param('id') id: string, @Req() req: any) {
    return this.communicationsService.deleteMessage(id, req.user.id);
  }
}
