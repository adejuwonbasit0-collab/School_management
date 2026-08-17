import { Injectable, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue } from 'bull';
import { OnEvent } from '@nestjs/event-emitter';
import { PrismaService } from '../../database/prisma.service';
import { ConfigService } from '@nestjs/config';
import * as nodemailer from 'nodemailer';
import * as handlebars from 'handlebars';

@Injectable()
export class NotificationsService {
  private readonly logger = new Logger(NotificationsService.name);
  private transporter: nodemailer.Transporter;

  constructor(
    private readonly prisma: PrismaService,
    private readonly config: ConfigService,
    @InjectQueue('notifications') private readonly notificationQueue: Queue,
  ) {
    this.setupMailTransporter();
  }

  private setupMailTransporter() {
    this.transporter = nodemailer.createTransport({
      host: this.config.get('mail.host'),
      port: this.config.get('mail.port'),
      secure: this.config.get('mail.secure'),
      auth: {
        user: this.config.get('mail.user'),
        pass: this.config.get('mail.password'),
      },
    });
  }

  // ─── Event Listeners ─────────────────────────────────────────────────────────
  @OnEvent('auth.registered')
  async handleUserRegistered(payload: any) {
    await this.sendEmail({
      to: payload.email,
      subject: 'Welcome to EduCore - Verify Your Email',
      html: this.buildEmailTemplate('verify-email', {
        firstName: payload.firstName,
        verificationLink: `${this.config.get('app.frontendUrl')}/verify-email?token=${payload.verificationToken}`,
      }),
    });
  }

  @OnEvent('auth.forgotPassword')
  async handleForgotPassword(payload: any) {
    await this.sendEmail({
      to: payload.email,
      subject: 'Reset Your EduCore Password',
      html: this.buildEmailTemplate('reset-password', {
        firstName: payload.firstName,
        resetLink: `${this.config.get('app.frontendUrl')}/reset-password?token=${payload.token}`,
      }),
    });
  }

  @OnEvent('finance.payment.completed')
  async handlePaymentCompleted(payload: any) {
    await this.notificationQueue.add('payment-receipt', payload, {
      attempts: 3,
      backoff: { type: 'exponential', delay: 5000 },
    });
  }

  @OnEvent('attendance.absent')
  async handleStudentAbsent(payload: any) {
    // Get parents of absent students
    const studentParents = await this.prisma.studentParent.findMany({
      where: { studentId: { in: payload.studentIds } },
      include: {
        student: {
          include: { user: { select: { firstName: true, lastName: true } } },
        },
        parent: {
          include: { user: { select: { email: true, phone: true, firstName: true } } },
        },
      },
    });

    for (const sp of studentParents) {
      if (sp.parent.user.email) {
        await this.notificationQueue.add('absent-notification', {
          parentEmail: sp.parent.user.email,
          parentName: sp.parent.user.firstName,
          studentName: `${sp.student.user.firstName} ${sp.student.user.lastName}`,
          date: payload.date,
          schoolId: payload.schoolId,
        });
      }
    }
  }

  @OnEvent('student.created')
  async handleStudentCreated(payload: any) {
    await this.createInAppNotification({
      schoolId: payload.schoolId,
      title: 'New Student Added',
      body: `Student ${payload.admissionNo} has been successfully enrolled`,
      type: 'IN_APP',
      audience: ['admin', 'academic-administrator'],
    });
  }

  // ─── Send Methods ────────────────────────────────────────────────────────────
  async sendEmail(options: { to: string; subject: string; html: string; from?: string }) {
    try {
      await this.transporter.sendMail({
        from: options.from || `"EduCore" <${this.config.get('mail.from')}>`,
        to: options.to,
        subject: options.subject,
        html: options.html,
      });
    } catch (error) {
      this.logger.error(`Failed to send email to ${options.to}: ${error.message}`);
    }
  }

  async sendSms(phone: string, message: string) {
    try {
      // Twilio implementation
      const accountSid = this.config.get('sms.twilioAccountSid');
      const authToken = this.config.get('sms.twilioAuthToken');
      if (!accountSid || !authToken) {
        this.logger.warn('SMS not configured');
        return;
      }
      const client = require('twilio')(accountSid, authToken);
      await client.messages.create({
        body: message,
        from: this.config.get('sms.twilioFrom'),
        to: phone,
      });
    } catch (error) {
      this.logger.error(`Failed to send SMS to ${phone}: ${error.message}`);
    }
  }

  async createInAppNotification(data: {
    schoolId: string;
    title: string;
    body: string;
    type: string;
    userId?: string;
    audience?: string[];
    notificationData?: any;
  }) {
    if (data.userId) {
      return this.prisma.notification.create({
        data: {
          userId: data.userId,
          type: 'IN_APP',
          title: data.title,
          body: data.body,
          data: data.notificationData,
          status: 'SENT',
          sentAt: new Date(),
        },
      });
    }
  }

  async sendNotification(data: {
    schoolId?: string;
    title: string;
    body: string;
    type?: string;
    userId?: string;
    audience?: string[];
    data?: any;
    notificationData?: any;
  }) {
    return this.createInAppNotification({
      schoolId: data.schoolId || '',
      title: data.title,
      body: data.body,
      type: data.type || 'IN_APP',
      userId: data.userId,
      audience: data.audience,
      notificationData: data.notificationData ?? data.data,
    });
  }

  // ─── Get User Notifications ──────────────────────────────────────────────────
  async getUserNotifications(userId: string, page = 1, limit = 20) {
    const skip = (page - 1) * limit;
    const [notifications, total, unreadCount] = await Promise.all([
      this.prisma.notification.findMany({
        where: { userId },
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.notification.count({ where: { userId } }),
      this.prisma.notification.count({ where: { userId, readAt: null, status: 'SENT' } }),
    ]);

    return {
      data: notifications,
      meta: { total, page, limit, totalPages: Math.ceil(total / limit), unreadCount },
    };
  }

  async markAsRead(userId: string, notificationId: string) {
    return this.prisma.notification.updateMany({
      where: { id: notificationId, userId },
      data: { readAt: new Date() },
    });
  }

  async markAllAsRead(userId: string) {
    return this.prisma.notification.updateMany({
      where: { userId, readAt: null },
      data: { readAt: new Date() },
    });
  }

  // ─── Announcements ───────────────────────────────────────────────────────────
  async createAnnouncement(schoolId: string, data: any, createdBy: string) {
    return this.prisma.announcement.create({
      data: {
        schoolId,
        title: data.title,
        content: data.content,
        audience: data.audience,
        priority: data.priority || 'normal',
        publishAt: data.publishAt ? new Date(data.publishAt) : undefined,
        expiresAt: data.expiresAt ? new Date(data.expiresAt) : undefined,
        isPublished: data.isPublished || false,
        createdBy,
      },
    });
  }

  async getAnnouncements(schoolId: string, audience?: string) {
    return this.prisma.announcement.findMany({
      where: {
        schoolId,
        isPublished: true,
        OR: [{ expiresAt: null }, { expiresAt: { gt: new Date() } }],
      },
      orderBy: [{ priority: 'desc' }, { createdAt: 'desc' }],
      take: 50,
    });
  }

  // ─── Template Builder ────────────────────────────────────────────────────────
  private buildEmailTemplate(templateName: string, data: Record<string, any>): string {
    const templates: Record<string, string> = {
      'verify-email': `
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#1e40af;padding:20px;text-align:center">
            <h1 style="color:white;margin:0">EduCore</h1>
          </div>
          <div style="padding:30px">
            <h2>Welcome, {{firstName}}!</h2>
            <p>Please verify your email address to activate your account.</p>
            <a href="{{verificationLink}}" style="background:#1e40af;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;margin:20px 0">Verify Email</a>
            <p style="color:#666;font-size:12px">This link expires in 24 hours.</p>
          </div>
        </div>`,
      'reset-password': `
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#1e40af;padding:20px;text-align:center">
            <h1 style="color:white;margin:0">EduCore</h1>
          </div>
          <div style="padding:30px">
            <h2>Password Reset</h2>
            <p>Hi {{firstName}}, click below to reset your password.</p>
            <a href="{{resetLink}}" style="background:#dc2626;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;margin:20px 0">Reset Password</a>
            <p style="color:#666;font-size:12px">This link expires in 1 hour. If you did not request this, ignore this email.</p>
          </div>
        </div>`,
      'payment-receipt': `
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:#059669;padding:20px;text-align:center">
            <h1 style="color:white;margin:0">Payment Received</h1>
          </div>
          <div style="padding:30px">
            <p>Dear {{parentName}},</p>
            <p>Payment of <strong>{{currency}}{{amount}}</strong> for invoice <strong>{{invoiceNo}}</strong> has been received.</p>
            <p>Transaction Reference: {{transactionRef}}</p>
          </div>
        </div>`,
    };

    const template = handlebars.compile(templates[templateName] || '<p>{{body}}</p>');
    return template(data);
  }
}
