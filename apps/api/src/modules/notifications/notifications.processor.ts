import { Process, Processor } from '@nestjs/bull';
import { Logger } from '@nestjs/common';
import { Job } from 'bull';
import { NotificationsService } from './notifications.service';
import { PrismaService } from '../../database/prisma.service';

@Processor('notifications')
export class NotificationsProcessor {
  private readonly logger = new Logger(NotificationsProcessor.name);

  constructor(
    private readonly notificationsService: NotificationsService,
    private readonly prisma: PrismaService,
  ) {}

  @Process('payment-receipt')
  async handlePaymentReceipt(job: Job) {
    const { invoiceId, studentId, amount, schoolId } = job.data;
    try {
      const invoice = await this.prisma.feeInvoice.findUnique({
        where: { id: invoiceId },
        include: {
          student: {
            include: {
              user: { select: { email: true, firstName: true, lastName: true } },
              parents: {
                where: { isPrimary: true },
                include: {
                  parent: { include: { user: { select: { email: true, firstName: true } } } },
                },
              },
            },
          },
          payments: { where: { status: 'COMPLETED' }, orderBy: { createdAt: 'desc' }, take: 1 },
        },
      });

      if (!invoice) return;

      const payment = invoice.payments[0];
      const parentEmail = invoice.student.parents[0]?.parent?.user?.email;
      const parentName = invoice.student.parents[0]?.parent?.user?.firstName;

      if (parentEmail) {
        await this.notificationsService.sendEmail({
          to: parentEmail,
          subject: `Payment Receipt - Invoice ${invoice.invoiceNo}`,
          html: `
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
              <div style="background:#059669;padding:20px;text-align:center">
                <h1 style="color:white">Payment Receipt</h1>
              </div>
              <div style="padding:30px">
                <p>Dear ${parentName || 'Parent'},</p>
                <p>Payment received for <strong>${invoice.student.user.firstName} ${invoice.student.user.lastName}</strong></p>
                <table style="width:100%;border-collapse:collapse">
                  <tr><td style="padding:8px;border:1px solid #ddd"><strong>Invoice No</strong></td><td style="padding:8px;border:1px solid #ddd">${invoice.invoiceNo}</td></tr>
                  <tr><td style="padding:8px;border:1px solid #ddd"><strong>Amount Paid</strong></td><td style="padding:8px;border:1px solid #ddd">₦${Number(payment?.amount || 0).toLocaleString()}</td></tr>
                  <tr><td style="padding:8px;border:1px solid #ddd"><strong>Balance</strong></td><td style="padding:8px;border:1px solid #ddd">₦${(Number(invoice.totalAmount) - Number(invoice.paidAmount)).toLocaleString()}</td></tr>
                  <tr><td style="padding:8px;border:1px solid #ddd"><strong>Status</strong></td><td style="padding:8px;border:1px solid #ddd">${invoice.status}</td></tr>
                </table>
                <p style="color:#666;font-size:12px;margin-top:20px">Thank you for your payment.</p>
              </div>
            </div>
          `,
        });
      }
    } catch (error) {
      this.logger.error(`Payment receipt job failed: ${error.message}`);
      throw error;
    }
  }

  @Process('absent-notification')
  async handleAbsentNotification(job: Job) {
    const { parentEmail, parentName, studentName, date } = job.data;
    try {
      await this.notificationsService.sendEmail({
        to: parentEmail,
        subject: `Attendance Alert - ${studentName}`,
        html: `
          <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
            <div style="background:#dc2626;padding:20px;text-align:center">
              <h1 style="color:white">Attendance Alert</h1>
            </div>
            <div style="padding:30px">
              <p>Dear ${parentName},</p>
              <p>This is to inform you that <strong>${studentName}</strong> was marked absent on <strong>${new Date(date).toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</strong>.</p>
              <p>If this is unexpected, please contact the school immediately.</p>
            </div>
          </div>
        `,
      });
    } catch (error) {
      this.logger.error(`Absent notification job failed: ${error.message}`);
      throw error;
    }
  }
}
