import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { NotificationsService } from '../notifications/notifications.service';

@Injectable()
export class CommunicationsService {
  constructor(
    private prisma: PrismaService,
    private notifications: NotificationsService,
  ) {}

  // ─── Broadcast Messages ───────────────────────────────────────────────────

  async getBroadcasts(schoolId: string, query: { page?: number; limit?: number; status?: string }) {
    const { page = 1, limit = 20, status } = query;
    const where: any = { schoolId };
    if (status) where.status = status;

    const [data, total] = await Promise.all([
      this.prisma.broadcastMessage.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
      this.prisma.broadcastMessage.count({ where }),
    ]);

    return { data, total, page, limit, pages: Math.ceil(total / limit) };
  }

  async createBroadcast(schoolId: string, userId: string, dto: {
    subject?: string;
    body: string;
    audience: { type: 'all' | 'class' | 'role' | 'students' | 'parents' | 'staff'; value?: string };
    channels: string[];
    scheduledAt?: Date;
  }) {
    return this.prisma.broadcastMessage.create({
      data: {
        schoolId,
        sentBy: userId,
        subject: dto.subject,
        body: dto.body,
        audience: dto.audience,
        channels: dto.channels,
        status: dto.scheduledAt ? 'scheduled' : 'draft',
        sentAt: dto.scheduledAt,
      },
    });
  }

  async sendBroadcast(id: string, schoolId: string) {
    const broadcast = await this.prisma.broadcastMessage.findFirst({ where: { id, schoolId } });
    if (!broadcast) throw new NotFoundException('Broadcast not found');

    const recipients = await this.resolveRecipients(schoolId, broadcast.audience as any);

    // Send IN_APP notifications
    if ((broadcast.channels as string[]).includes('in_app')) {
      for (const userId of recipients) {
        await this.notifications.sendNotification({
          userId,
          type: 'IN_APP',
          title: broadcast.subject || 'School Announcement',
          body: broadcast.body,
          data: { broadcastId: id },
        });
      }
    }

    await this.prisma.broadcastMessage.update({
      where: { id },
      data: {
        status: 'sent',
        sentAt: new Date(),
        recipientCount: recipients.length,
      },
    });

    return { sent: recipients.length };
  }

  async deleteBroadcast(id: string, schoolId: string) {
    const broadcast = await this.prisma.broadcastMessage.findFirst({ where: { id, schoolId } });
    if (!broadcast) throw new NotFoundException('Broadcast not found');
    if (broadcast.status === 'sent') throw new Error('Cannot delete sent broadcasts');
    return this.prisma.broadcastMessage.delete({ where: { id } });
  }

  // ─── Notification Templates ───────────────────────────────────────────────

  async getTemplates(schoolId: string) {
    return this.prisma.notificationTemplate.findMany({
      where: { schoolId },
      orderBy: { name: 'asc' },
    });
  }

  async createTemplate(schoolId: string, dto: {
    name: string;
    type: 'EMAIL' | 'SMS' | 'PUSH' | 'IN_APP';
    subject?: string;
    body: string;
    variables?: Record<string, string>;
  }) {
    return this.prisma.notificationTemplate.create({
      data: { schoolId, ...dto },
    });
  }

  async updateTemplate(id: string, schoolId: string, dto: any) {
    const template = await this.prisma.notificationTemplate.findFirst({ where: { id, schoolId } });
    if (!template) throw new NotFoundException('Template not found');
    return this.prisma.notificationTemplate.update({ where: { id }, data: dto });
  }

  async deleteTemplate(id: string, schoolId: string) {
    const template = await this.prisma.notificationTemplate.findFirst({ where: { id, schoolId } });
    if (!template) throw new NotFoundException('Template not found');
    return this.prisma.notificationTemplate.delete({ where: { id } });
  }

  // ─── Messages ─────────────────────────────────────────────────────────────

  async getMessages(userId: string, type: 'inbox' | 'sent', page = 1, limit = 20) {
    const where = type === 'inbox' ? { receiverId: userId } : { senderId: userId };
    const [data, total] = await Promise.all([
      this.prisma.message.findMany({
        where: { ...where, parentId: null },
        include: {
          sender: { select: { firstName: true, lastName: true, avatar: true } },
          receiver: { select: { firstName: true, lastName: true, avatar: true } },
          replies: { select: { id: true, createdAt: true } },
        },
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
      this.prisma.message.count({ where: { ...where, parentId: null } }),
    ]);
    return { data, total, page, limit };
  }

  async getMessage(id: string, userId: string) {
    const msg = await this.prisma.message.findUnique({
      where: { id },
      include: {
        sender: { select: { firstName: true, lastName: true, avatar: true } },
        receiver: { select: { firstName: true, lastName: true, avatar: true } },
        replies: {
          include: {
            sender: { select: { firstName: true, lastName: true, avatar: true } },
          },
          orderBy: { createdAt: 'asc' },
        },
      },
    });

    if (!msg) throw new NotFoundException('Message not found');
    if (msg.receiverId !== userId && msg.senderId !== userId) {
      throw new NotFoundException('Message not found');
    }

    if (msg.receiverId === userId && !msg.isRead) {
      await this.prisma.message.update({ where: { id }, data: { isRead: true, readAt: new Date() } });
    }

    return msg;
  }

  async sendMessage(senderId: string, dto: {
    receiverId: string;
    subject?: string;
    body: string;
    attachments?: any[];
    parentId?: string;
  }) {
    const msg = await this.prisma.message.create({
      data: { senderId, ...dto },
      include: {
        sender: { select: { firstName: true, lastName: true } },
        receiver: { select: { firstName: true, lastName: true } },
      },
    });

    // In-app notification
    await this.notifications.sendNotification({
      userId: dto.receiverId,
      type: 'IN_APP',
      title: `New message from ${msg.sender.firstName}`,
      body: dto.subject || dto.body.slice(0, 80),
      data: { messageId: msg.id },
    });

    return msg;
  }

  async deleteMessage(id: string, userId: string) {
    const msg = await this.prisma.message.findFirst({
      where: { id, OR: [{ senderId: userId }, { receiverId: userId }] },
    });
    if (!msg) throw new NotFoundException('Message not found');
    return this.prisma.message.delete({ where: { id } });
  }

  async getUnreadCount(userId: string) {
    const count = await this.prisma.message.count({
      where: { receiverId: userId, isRead: false },
    });
    return { count };
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  private async resolveRecipients(schoolId: string, audience: { type: string; value?: string }): Promise<string[]> {
    switch (audience.type) {
      case 'all': {
        const users = await this.prisma.user.findMany({
          where: { schoolId },
          select: { id: true },
        });
        return users.map(u => u.id);
      }
      case 'students': {
        const students = await this.prisma.student.findMany({
          where: { schoolId },
          include: { user: { select: { id: true } } },
        });
        return students.map(s => s.user!.id);
      }
      case 'parents': {
        const parents = await this.prisma.parent.findMany({
          include: { user: { select: { id: true } } },
          where: { user: { schoolId } },
        });
        return parents.map(p => p.user!.id);
      }
      case 'staff': {
        const staff = await this.prisma.staff.findMany({
          where: { schoolId },
          include: { user: { select: { id: true } } },
        });
        return staff.map(s => s.user!.id);
      }
      case 'class': {
        if (!audience.value) return [];
        const enrollments = await this.prisma.studentEnrollment.findMany({
          where: { classRoomId: audience.value, isCurrent: true },
          include: { student: { include: { user: { select: { id: true } } } } },
        });
        return enrollments.map(e => e.student.user!.id);
      }
      default:
        return [];
    }
  }
}
