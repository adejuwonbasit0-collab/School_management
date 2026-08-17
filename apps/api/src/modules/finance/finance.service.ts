import {
  Injectable,
  NotFoundException,
  BadRequestException,
  ForbiddenException,
} from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { EventEmitter2 } from '@nestjs/event-emitter';
import {
  CreateFeeStructureDto,
  CreateInvoiceDto,
  RecordPaymentDto,
  RequestReversalDto,
  FinanceQueryDto,
  CreateExpenseDto,
} from './dto';
import { nanoid } from 'nanoid';
import { PaymentGateway, TransactionStatus } from '@prisma/client';

@Injectable()
export class FinanceService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  // ─── Dashboard Stats ─────────────────────────────────────────────────────────
  async getDashboardStats(schoolId: string) {
    const currentYear = await this.prisma.academicYear.findFirst({
      where: { schoolId, isCurrent: true },
    });

    const [totalInvoiced, totalCollected, unpaidCount, overdueCount, recentPayments] =
      await Promise.all([
        this.prisma.feeInvoice.aggregate({
          where: { schoolId },
          _sum: { totalAmount: true },
        }),
        this.prisma.payment.aggregate({
          where: { schoolId, status: 'COMPLETED' },
          _sum: { amount: true },
        }),
        this.prisma.feeInvoice.count({
          where: { schoolId, status: { in: ['UNPAID', 'PARTIAL'] } },
        }),
        this.prisma.feeInvoice.count({
          where: {
            schoolId,
            status: { in: ['UNPAID', 'PARTIAL'] },
            dueDate: { lt: new Date() },
          },
        }),
        this.prisma.payment.findMany({
          where: { schoolId, status: 'COMPLETED' },
          include: {
            invoice: {
              include: {
                student: {
                  include: {
                    user: { select: { firstName: true, lastName: true } },
                  },
                },
              },
            },
          },
          orderBy: { paidAt: 'desc' },
          take: 10,
        }),
      ]);

    const totalInvoicedAmount = Number(totalInvoiced._sum.totalAmount || 0);
    const totalCollectedAmount = Number(totalCollected._sum.amount || 0);
    const outstanding = totalInvoicedAmount - totalCollectedAmount;

    const byGateway = recentPayments.reduce((acc, p) => {
      acc[p.gateway] = (acc[p.gateway] || 0) + Number(p.amount);
      return acc;
    }, {} as Record<string, number>);

    // Monthly trend for the current year
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const yearStart = new Date(new Date().getFullYear(), 0, 1);
    const [yearInvoices, yearPayments] = await Promise.all([
      this.prisma.feeInvoice.findMany({ where: { schoolId, createdAt: { gte: yearStart } }, select: { totalAmount: true, createdAt: true } }),
      this.prisma.payment.findMany({ where: { schoolId, status: 'COMPLETED', paidAt: { gte: yearStart } }, select: { amount: true, paidAt: true } }),
    ]);
    const monthlyTrend = monthNames.map((month, i) => ({
      month,
      invoiced: yearInvoices.filter((inv) => inv.createdAt.getMonth() === i).reduce((s, inv) => s + Number(inv.totalAmount), 0),
      collected: yearPayments.filter((p) => p.paidAt && p.paidAt.getMonth() === i).reduce((s, p) => s + Number(p.amount), 0),
    }));

    return {
      totalInvoiced: totalInvoicedAmount,
      totalCollected: totalCollectedAmount,
      outstanding,
      unpaidCount,
      overdueCount,
      collectionRate: totalInvoicedAmount > 0
        ? Math.round((totalCollectedAmount / totalInvoicedAmount) * 100)
        : 0,
      recentPayments,
      byGateway,
      monthlyTrend,
    };
  }

  // ─── Fee Structures ──────────────────────────────────────────────────────────
  async createFeeStructure(schoolId: string, dto: CreateFeeStructureDto) {
    const structure = await this.prisma.feeStructure.create({
      data: {
        schoolId,
        academicYearId: dto.academicYearId,
        classRoomId: dto.classRoomId,
        name: dto.name,
        items: {
          create: dto.items.map((item) => ({
            name: item.name,
            amount: item.amount,
            isOptional: item.isOptional || false,
            dueDate: item.dueDate ? new Date(item.dueDate) : undefined,
          })),
        },
      },
      include: { items: true, academicYear: { select: { name: true } } },
    });

    return structure;
  }

  async getFeeStructures(schoolId: string, academicYearId?: string) {
    return this.prisma.feeStructure.findMany({
      where: {
        schoolId,
        ...(academicYearId && { academicYearId }),
      },
      include: {
        items: true,
        academicYear: { select: { id: true, name: true } },
        _count: { select: { invoices: true } },
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  // ─── Invoices ────────────────────────────────────────────────────────────────
  async createInvoice(schoolId: string, dto: CreateInvoiceDto) {
    const student = await this.prisma.student.findFirst({
      where: { id: dto.studentId, schoolId },
    });
    if (!student) throw new NotFoundException('Student not found');

    const invoiceNo = await this.generateInvoiceNo(schoolId);
    const totalAmount = dto.items.reduce((sum, item) => sum + item.amount, 0);

    const invoice = await this.prisma.feeInvoice.create({
      data: {
        schoolId,
        studentId: dto.studentId,
        feeStructureId: dto.feeStructureId,
        termId: dto.termId,
        invoiceNo,
        totalAmount,
        discountAmount: dto.discountAmount || 0,
        dueDate: dto.dueDate ? new Date(dto.dueDate) : undefined,
        status: 'UNPAID',
        items: {
          create: dto.items.map((item) => ({
            name: item.name,
            amount: item.amount,
            discount: item.discount || 0,
          })),
        },
      },
      include: {
        student: {
          include: { user: { select: { firstName: true, lastName: true, email: true } } },
        },
        items: true,
      },
    });

    this.eventEmitter.emit('finance.invoice.created', {
      invoiceId: invoice.id,
      studentId: dto.studentId,
      schoolId,
      amount: totalAmount,
    });

    return invoice;
  }

  async getInvoices(schoolId: string, query: FinanceQueryDto) {
    const { page = 1, limit = 20, search, status, studentId, termId } = query;
    const skip = (page - 1) * limit;

    const where: any = {
      schoolId,
      ...(status && { status }),
      ...(studentId && { studentId }),
      ...(termId && { termId }),
      ...(search && {
        OR: [
          { invoiceNo: { contains: search, mode: 'insensitive' } },
          {
            student: {
              user: {
                OR: [
                  { firstName: { contains: search, mode: 'insensitive' } },
                  { lastName: { contains: search, mode: 'insensitive' } },
                ],
              },
            },
          },
        ],
      }),
    };

    const [invoices, total] = await Promise.all([
      this.prisma.feeInvoice.findMany({
        where,
        skip,
        take: limit,
        include: {
          student: {
            include: {
              user: { select: { firstName: true, lastName: true, avatar: true } },
              enrollments: {
                where: { isCurrent: true },
                include: { classRoom: { select: { name: true, section: true } } },
              },
            },
          },
          items: true,
          payments: {
            where: { status: 'COMPLETED' },
            select: { amount: true, paidAt: true, gateway: true },
          },
        },
        orderBy: { createdAt: 'desc' },
      }),
      this.prisma.feeInvoice.count({ where }),
    ]);

    return {
      data: invoices,
      meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
    };
  }

  async getInvoice(schoolId: string, id: string) {
    const invoice = await this.prisma.feeInvoice.findFirst({
      where: { id, schoolId },
      include: {
        student: {
          include: {
            user: true,
            enrollments: {
              where: { isCurrent: true },
              include: { classRoom: true },
            },
          },
        },
        items: true,
        payments: {
          include: { reversal: true },
          orderBy: { createdAt: 'desc' },
        },
        term: { select: { name: true, type: true } },
        feeStructure: { select: { name: true } },
      },
    });

    if (!invoice) throw new NotFoundException('Invoice not found');
    return invoice;
  }

  // ─── Payments ────────────────────────────────────────────────────────────────
  async recordPayment(schoolId: string, invoiceId: string, dto: RecordPaymentDto) {
    const invoice = await this.prisma.feeInvoice.findFirst({
      where: { id: invoiceId, schoolId },
      include: { payments: { where: { status: 'COMPLETED' } } },
    });

    if (!invoice) throw new NotFoundException('Invoice not found');
    if (invoice.status === 'PAID') throw new BadRequestException('Invoice is already paid');
    if (invoice.status === 'WAIVED') throw new BadRequestException('Invoice has been waived');

    const alreadyPaid = invoice.payments.reduce(
      (sum, p) => sum + Number(p.amount),
      0,
    );
    const outstanding = Number(invoice.totalAmount) - Number(invoice.discountAmount) - alreadyPaid;

    if (dto.amount > outstanding) {
      throw new BadRequestException(
        `Payment amount (${dto.amount}) exceeds outstanding balance (${outstanding})`,
      );
    }

    const transactionRef = `TXN${Date.now()}${nanoid(6).toUpperCase()}`;

    const payment = await this.prisma.$transaction(async (tx) => {
      const newPayment = await tx.payment.create({
        data: {
          schoolId,
          invoiceId,
          transactionRef,
          gateway: dto.gateway,
          amount: dto.amount,
          currency: dto.currency || 'NGN',
          status: 'COMPLETED',
          gatewayRef: dto.gatewayRef,
          paidAt: new Date(),
          metadata: dto.metadata,
        },
      });

      // Update invoice
      const newPaidAmount = alreadyPaid + dto.amount;
      const newStatus =
        newPaidAmount >= outstanding + alreadyPaid ? 'PAID' : 'PARTIAL';

      await tx.feeInvoice.update({
        where: { id: invoiceId },
        data: {
          paidAmount: newPaidAmount,
          status: newStatus,
        },
      });

      return newPayment;
    });

    this.eventEmitter.emit('finance.payment.completed', {
      paymentId: payment.id,
      invoiceId,
      studentId: invoice.studentId,
      amount: dto.amount,
      schoolId,
    });

    return payment;
  }

  // ─── Bulk Invoice Generation ─────────────────────────────────────────────────
  async generateBulkInvoices(
    schoolId: string,
    feeStructureId: string,
    classRoomId: string,
    academicYearId: string,
  ) {
    const structure = await this.prisma.feeStructure.findFirst({
      where: { id: feeStructureId, schoolId },
      include: { items: true },
    });
    if (!structure) throw new NotFoundException('Fee structure not found');

    const enrollments = await this.prisma.studentEnrollment.findMany({
      where: { classRoomId, academicYearId, isCurrent: true },
      include: { student: true },
    });

    const results = { created: 0, skipped: 0, errors: [] as string[] };

    for (const enrollment of enrollments) {
      try {
        const existing = await this.prisma.feeInvoice.findFirst({
          where: {
            studentId: enrollment.studentId,
            feeStructureId,
          },
        });

        if (existing) {
          results.skipped++;
          continue;
        }

        await this.createInvoice(schoolId, {
          studentId: enrollment.studentId,
          feeStructureId,
          items: structure.items.map((i) => ({
            name: i.name,
            amount: Number(i.amount),
            discount: 0,
          })),
        });

        results.created++;
      } catch (err) {
        results.errors.push(`Student ${enrollment.studentId}: ${err.message}`);
      }
    }

    return results;
  }

  // ─── Payment Reversal ────────────────────────────────────────────────────────
  async requestReversal(schoolId: string, paymentId: string, dto: RequestReversalDto, requestedBy: string) {
    const payment = await this.prisma.payment.findFirst({
      where: { id: paymentId, schoolId },
    });
    if (!payment) throw new NotFoundException('Payment not found');
    if (payment.status !== 'COMPLETED') {
      throw new BadRequestException('Only completed payments can be reversed');
    }

    const existing = await this.prisma.paymentReversal.findUnique({
      where: { paymentId },
    });
    if (existing) throw new BadRequestException('Reversal already requested for this payment');

    return this.prisma.paymentReversal.create({
      data: {
        paymentId,
        requestedBy,
        reason: dto.reason,
        status: 'PENDING',
      },
    });
  }

  async approveReversal(schoolId: string, reversalId: string, approvedBy: string) {
    const reversal = await this.prisma.paymentReversal.findUnique({
      where: { id: reversalId },
      include: {
        payment: { include: { invoice: true } },
      },
    });

    if (!reversal) throw new NotFoundException('Reversal not found');
    if (reversal.payment.invoice.schoolId !== schoolId) throw new ForbiddenException();
    if (reversal.status !== 'PENDING') throw new BadRequestException('Reversal is not pending');

    await this.prisma.$transaction(async (tx) => {
      // Update reversal
      await tx.paymentReversal.update({
        where: { id: reversalId },
        data: { status: 'COMPLETED', approvedBy, approvedAt: new Date() },
      });

      // Update payment status
      await tx.payment.update({
        where: { id: reversal.paymentId },
        data: { status: 'REVERSED' },
      });

      // Update invoice paid amount
      const newPaidAmount =
        Number(reversal.payment.invoice.paidAmount) - Number(reversal.payment.amount);

      await tx.feeInvoice.update({
        where: { id: reversal.payment.invoiceId },
        data: {
          paidAmount: Math.max(0, newPaidAmount),
          status: newPaidAmount <= 0 ? 'UNPAID' : 'PARTIAL',
        },
      });
    });

    return { message: 'Reversal approved and processed' };
  }

  // ─── Expenses ────────────────────────────────────────────────────────────────
  async createExpense(schoolId: string, dto: CreateExpenseDto) {
    return this.prisma.expense.create({
      data: {
        schoolId,
        title: dto.title,
        description: dto.description,
        amount: dto.amount,
        date: new Date(dto.date),
        paymentMethod: dto.paymentMethod,
        receiptUrl: dto.receiptUrl,
      },
    });
  }

  async getExpenses(schoolId: string, query: FinanceQueryDto) {
    const { page = 1, limit = 20 } = query;
    const skip = (page - 1) * limit;

    const [expenses, total] = await Promise.all([
      this.prisma.expense.findMany({
        where: { schoolId },
        skip,
        take: limit,
        orderBy: { date: 'desc' },
      }),
      this.prisma.expense.count({ where: { schoolId } }),
    ]);

    return {
      data: expenses,
      meta: { total, page, limit, totalPages: Math.ceil(total / limit) },
    };
  }

  // ─── Income Report ───────────────────────────────────────────────────────────
  async getIncomeReport(schoolId: string, startDate: string, endDate: string) {
    const payments = await this.prisma.payment.findMany({
      where: {
        schoolId,
        status: 'COMPLETED',
        paidAt: {
          gte: new Date(startDate),
          lte: new Date(endDate),
        },
      },
      include: {
        invoice: {
          include: {
            student: {
              include: {
                user: { select: { firstName: true, lastName: true } },
                enrollments: {
                  where: { isCurrent: true },
                  include: { classRoom: { select: { name: true } } },
                },
              },
            },
          },
        },
      },
      orderBy: { paidAt: 'desc' },
    });

    const totalAmount = payments.reduce((sum, p) => sum + Number(p.amount), 0);
    const byGateway = payments.reduce((acc, p) => {
      acc[p.gateway] = (acc[p.gateway] || 0) + Number(p.amount);
      return acc;
    }, {} as Record<string, number>);

    return {
      payments,
      summary: {
        total: totalAmount,
        count: payments.length,
        byGateway,
      },
    };
  }

  // ─── Payment Gateways ────────────────────────────────────────────────────────
  async getGatewayConfigs(schoolId: string) {
    return this.prisma.paymentGatewayConfig.findMany({
      where: { schoolId },
      select: {
        id: true,
        gateway: true,
        isEnabled: true,
        isLive: true,
        displayName: true,
        logoUrl: true,
        // Never return config with keys
      },
    });
  }

  async upsertGatewayConfig(schoolId: string, gateway: PaymentGateway, data: any) {
    return this.prisma.paymentGatewayConfig.upsert({
      where: { schoolId_gateway: { schoolId, gateway } },
      create: {
        schoolId,
        gateway,
        isEnabled: data.isEnabled ?? false,
        isLive: data.isLive ?? false,
        config: data.config,
        displayName: data.displayName,
        logoUrl: data.logoUrl,
      },
      update: {
        isEnabled: data.isEnabled,
        isLive: data.isLive,
        config: data.config,
        displayName: data.displayName,
        logoUrl: data.logoUrl,
      },
      select: {
        id: true,
        gateway: true,
        isEnabled: true,
        isLive: true,
        displayName: true,
        logoUrl: true,
      },
    });
  }

  // ─── Private Helpers ─────────────────────────────────────────────────────────
  private async generateInvoiceNo(schoolId: string): Promise<string> {
    const year = new Date().getFullYear();
    const count = await this.prisma.feeInvoice.count({ where: { schoolId } });
    return `INV${year}${String(count + 1).padStart(5, '0')}`;
  }
}
