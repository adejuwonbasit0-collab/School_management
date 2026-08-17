import {
  Controller,
  Get,
  Post,
  Put,
  Body,
  Param,
  Query,
  UseGuards,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { FinanceService } from './finance.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import {
  CreateFeeStructureDto,
  CreateInvoiceDto,
  RecordPaymentDto,
  RequestReversalDto,
  FinanceQueryDto,
  CreateExpenseDto,
} from './dto';
import { PaymentGateway } from '@prisma/client';

@ApiTags('Finance')
@ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'finance', version: '1' })
export class FinanceController {
  constructor(private readonly financeService: FinanceService) {}

  @Get('dashboard')
  @RequirePermissions('finance:reports:READ')
  getDashboard(@SchoolId() schoolId: string) {
    return this.financeService.getDashboardStats(schoolId);
  }

  // ─── Fee Structures ──────────────────────────────────────────────────────────
  @Post('fee-structures')
  @RequirePermissions('finance:fee-structures:CREATE')
  createFeeStructure(@SchoolId() schoolId: string, @Body() dto: CreateFeeStructureDto) {
    return this.financeService.createFeeStructure(schoolId, dto);
  }

  @Get('fee-structures')
  @RequirePermissions('finance:fee-structures:READ')
  getFeeStructures(@SchoolId() schoolId: string, @Query('academicYearId') academicYearId?: string) {
    return this.financeService.getFeeStructures(schoolId, academicYearId);
  }

  // ─── Invoices ────────────────────────────────────────────────────────────────
  @Post('invoices')
  @RequirePermissions('finance:invoices:CREATE')
  createInvoice(@SchoolId() schoolId: string, @Body() dto: CreateInvoiceDto) {
    return this.financeService.createInvoice(schoolId, dto);
  }

  @Get('invoices')
  @RequirePermissions('finance:invoices:READ')
  getInvoices(@SchoolId() schoolId: string, @Query() query: FinanceQueryDto) {
    return this.financeService.getInvoices(schoolId, query);
  }

  @Get('invoices/:id')
  @RequirePermissions('finance:invoices:READ')
  getInvoice(@SchoolId() schoolId: string, @Param('id') id: string) {
    return this.financeService.getInvoice(schoolId, id);
  }

  @Post('invoices/bulk-generate')
  @RequirePermissions('finance:invoices:CREATE')
  generateBulkInvoices(
    @SchoolId() schoolId: string,
    @Body() body: { feeStructureId: string; classRoomId: string; academicYearId: string },
  ) {
    return this.financeService.generateBulkInvoices(
      schoolId,
      body.feeStructureId,
      body.classRoomId,
      body.academicYearId,
    );
  }

  // ─── Payments ────────────────────────────────────────────────────────────────
  @Post('invoices/:id/payments')
  @RequirePermissions('finance:payments:CREATE')
  recordPayment(
    @SchoolId() schoolId: string,
    @Param('id') invoiceId: string,
    @Body() dto: RecordPaymentDto,
  ) {
    return this.financeService.recordPayment(schoolId, invoiceId, dto);
  }

  @Post('payments/:id/reversal')
  @RequirePermissions('finance:payments:MANAGE')
  requestReversal(
    @SchoolId() schoolId: string,
    @Param('id') paymentId: string,
    @Body() dto: RequestReversalDto,
    @CurrentUser('id') userId: string,
  ) {
    return this.financeService.requestReversal(schoolId, paymentId, dto, userId);
  }

  @Put('reversals/:id/approve')
  @RequirePermissions('finance:payments:APPROVE')
  approveReversal(
    @SchoolId() schoolId: string,
    @Param('id') reversalId: string,
    @CurrentUser('id') userId: string,
  ) {
    return this.financeService.approveReversal(schoolId, reversalId, userId);
  }

  // ─── Expenses ────────────────────────────────────────────────────────────────
  @Post('expenses')
  @RequirePermissions('finance:expenses:CREATE')
  createExpense(@SchoolId() schoolId: string, @Body() dto: CreateExpenseDto) {
    return this.financeService.createExpense(schoolId, dto);
  }

  @Get('expenses')
  @RequirePermissions('finance:expenses:READ')
  getExpenses(@SchoolId() schoolId: string, @Query() query: FinanceQueryDto) {
    return this.financeService.getExpenses(schoolId, query);
  }

  // ─── Reports ─────────────────────────────────────────────────────────────────
  @Get('reports/income')
  @RequirePermissions('finance:reports:READ')
  getIncomeReport(
    @SchoolId() schoolId: string,
    @Query('startDate') startDate: string,
    @Query('endDate') endDate: string,
  ) {
    return this.financeService.getIncomeReport(schoolId, startDate, endDate);
  }

  // ─── Payment Gateways ────────────────────────────────────────────────────────
  @Get('gateways')
  @RequirePermissions('finance:gateways:READ')
  getGateways(@SchoolId() schoolId: string) {
    return this.financeService.getGatewayConfigs(schoolId);
  }

  @Put('gateways/:gateway')
  @RequirePermissions('finance:gateways:MANAGE')
  updateGateway(
    @SchoolId() schoolId: string,
    @Param('gateway') gateway: PaymentGateway,
    @Body() data: any,
  ) {
    return this.financeService.upsertGatewayConfig(schoolId, gateway, data);
  }
}
