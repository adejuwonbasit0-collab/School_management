import {
  IsString,
  IsEmail,
  IsOptional,
  IsEnum,
  IsArray,
  IsBoolean,
  IsDateString,
  IsInt,
  Min,
  Max,
  IsNotEmpty,
  ValidateNested,
} from 'class-validator';
import { Type, Transform } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Gender, BloodGroup } from '@prisma/client';

export class ParentDto {
  @IsString()
  firstName: string;

  @IsString()
  lastName: string;

  @IsEmail()
  @IsOptional()
  email?: string;

  @IsString()
  @IsOptional()
  phone?: string;

  @IsString()
  @IsOptional()
  relationship?: string;

  @IsBoolean()
  @IsOptional()
  isPrimary?: boolean;

  @IsString()
  @IsOptional()
  occupation?: string;

  @IsString()
  @IsOptional()
  workplace?: string;
}

export class CreateStudentDto {
  @ApiProperty()
  @IsEmail()
  @Transform(({ value }) => value?.toLowerCase().trim())
  email: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  password?: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  firstName: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  lastName: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  middleName?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  phone?: string;

  @ApiPropertyOptional({ enum: Gender })
  @IsEnum(Gender)
  @IsOptional()
  gender?: Gender;

  @ApiPropertyOptional()
  @IsDateString()
  @IsOptional()
  dateOfBirth?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  address?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  city?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  state?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  country?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  avatar?: string;

  @ApiPropertyOptional({ enum: BloodGroup })
  @IsEnum(BloodGroup)
  @IsOptional()
  bloodGroup?: BloodGroup;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  nationality?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  religion?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  motherTongue?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  previousSchool?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  medicalConditions?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  allergies?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  disabilities?: string;

  @ApiPropertyOptional()
  @IsDateString()
  @IsOptional()
  admissionDate?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  classRoomId?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  academicYearId?: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  rollNumber?: string;

  @ApiPropertyOptional({ type: [ParentDto] })
  @IsArray()
  @IsOptional()
  @ValidateNested({ each: true })
  @Type(() => ParentDto)
  parents?: ParentDto[];
}

export class UpdateStudentDto extends CreateStudentDto {}

export class EnrollStudentDto {
  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  classRoomId: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  academicYearId: string;

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  rollNumber?: string;
}

export class PromoteStudentsDto {
  @ApiProperty()
  @IsArray()
  @IsString({ each: true })
  studentIds: string[];

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  fromClassId: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  toClassId: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  academicYearId: string;
}

export class StudentQueryDto {
  @IsInt()
  @Min(1)
  @IsOptional()
  @Transform(({ value }) => parseInt(value))
  page?: number = 1;

  @IsInt()
  @Min(1)
  @Max(100)
  @IsOptional()
  @Transform(({ value }) => parseInt(value))
  limit?: number = 20;

  @IsString()
  @IsOptional()
  search?: string;

  @IsString()
  @IsOptional()
  classRoomId?: string;

  @IsString()
  @IsOptional()
  academicYearId?: string;

  @IsString()
  @IsOptional()
  sortBy?: string = 'createdAt';

  @IsString()
  @IsOptional()
  sortOrder?: 'asc' | 'desc' = 'desc';
}
