import {
  IsString, IsNotEmpty, IsOptional, IsArray, IsNumber,
  IsBoolean, IsDateString, IsEnum, IsInt, Min, Max,
  ValidateNested, IsPositive,
} from 'class-validator';
import { Type, Transform } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { PaymentGateway, FeeStatus } from '@prisma/client';

export class FeeItemDto {
  @IsString() @IsNotEmpty() name: string;
  @IsNumber() @IsPositive() amount: number;
  @IsBoolean() @IsOptional() isOptional?: boolean;
  @IsDateString() @IsOptional() dueDate?: string;
}

export class CreateFeeStructureDto {
  @ApiProperty() @IsString() @IsNotEmpty() name: string;
  @ApiProperty() @IsString() @IsNotEmpty() academicYearId: string;
  @ApiPropertyOptional() @IsString() @IsOptional() classRoomId?: string;
  @ApiProperty({ type: [FeeItemDto] })
  @IsArray() @ValidateNested({ each: true }) @Type(() => FeeItemDto)
  items: FeeItemDto[];
}

export class InvoiceItemDto {
  @IsString() @IsNotEmpty() name: string;
  @IsNumber() @IsPositive() amount: number;
  @IsNumber() @Min(0) @IsOptional() discount?: number;
}

export class CreateInvoiceDto {
  @ApiProperty() @IsString() @IsNotEmpty() studentId: string;
  @ApiPropertyOptional() @IsString() @IsOptional() feeStructureId?: string;
  @ApiPropertyOptional() @IsString() @IsOptional() termId?: string;
  @ApiPropertyOptional() @IsNumber() @Min(0) @IsOptional() discountAmount?: number;
  @ApiPropertyOptional() @IsDateString() @IsOptional() dueDate?: string;
  @ApiProperty({ type: [InvoiceItemDto] })
  @IsArray() @ValidateNested({ each: true }) @Type(() => InvoiceItemDto)
  items: InvoiceItemDto[];
}

export class RecordPaymentDto {
  @ApiProperty() @IsNumber() @IsPositive() amount: number;
  @ApiProperty({ enum: PaymentGateway }) @IsEnum(PaymentGateway) gateway: PaymentGateway;
  @ApiPropertyOptional() @IsString() @IsOptional() currency?: string;
  @ApiPropertyOptional() @IsString() @IsOptional() gatewayRef?: string;
  @ApiPropertyOptional() @IsOptional() metadata?: any;
}

export class RequestReversalDto {
  @ApiProperty() @IsString() @IsNotEmpty() reason: string;
}

export class CreateExpenseDto {
  @ApiProperty() @IsString() @IsNotEmpty() title: string;
  @ApiPropertyOptional() @IsString() @IsOptional() description?: string;
  @ApiProperty() @IsNumber() @IsPositive() amount: number;
  @ApiProperty() @IsDateString() date: string;
  @ApiPropertyOptional() @IsString() @IsOptional() paymentMethod?: string;
  @ApiPropertyOptional() @IsString() @IsOptional() receiptUrl?: string;
}

export class FinanceQueryDto {
  @IsInt() @Min(1) @IsOptional() @Transform(({ value }) => parseInt(value)) page?: number = 1;
  @IsInt() @Min(1) @Max(100) @IsOptional() @Transform(({ value }) => parseInt(value)) limit?: number = 20;
  @IsString() @IsOptional() search?: string;
  @IsEnum(FeeStatus) @IsOptional() status?: FeeStatus;
  @IsString() @IsOptional() studentId?: string;
  @IsString() @IsOptional() termId?: string;
  @IsDateString() @IsOptional() startDate?: string;
  @IsDateString() @IsOptional() endDate?: string;
}
