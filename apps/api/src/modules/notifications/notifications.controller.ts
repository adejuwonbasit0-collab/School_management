import { Controller, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { NotificationsService } from './notifications.service';
import { JwtAuthGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, SchoolId } from '../../decorators/current-user.decorator';

@ApiTags('Notifications')
@ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard)
@Controller({ path: 'notifications', version: '1' })
export class NotificationsController {
  constructor(private readonly notificationsService: NotificationsService) {}

  @Get()
  @ApiOperation({ summary: 'Get user notifications' })
  getNotifications(
    @CurrentUser('id') userId: string,
    @Query('page') page: number,
    @Query('limit') limit: number,
  ) {
    return this.notificationsService.getUserNotifications(userId, page, limit);
  }

  @Put(':id/read')
  @ApiOperation({ summary: 'Mark notification as read' })
  markAsRead(@CurrentUser('id') userId: string, @Param('id') id: string) {
    return this.notificationsService.markAsRead(userId, id);
  }

  @Put('read-all')
  @ApiOperation({ summary: 'Mark all notifications as read' })
  markAllAsRead(@CurrentUser('id') userId: string) {
    return this.notificationsService.markAllAsRead(userId);
  }

  @Post('announcements')
  @ApiOperation({ summary: 'Create announcement' })
  createAnnouncement(
    @SchoolId() schoolId: string,
    @Body() data: any,
    @CurrentUser('id') userId: string,
  ) {
    return this.notificationsService.createAnnouncement(schoolId, data, userId);
  }

  @Get('announcements')
  @ApiOperation({ summary: 'Get announcements' })
  getAnnouncements(@SchoolId() schoolId: string) {
    return this.notificationsService.getAnnouncements(schoolId);
  }
}
