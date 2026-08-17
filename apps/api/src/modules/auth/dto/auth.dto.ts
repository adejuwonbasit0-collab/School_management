import { IsEmail, IsString, IsNotEmpty, IsOptional, MinLength, MaxLength, Matches } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Transform } from 'class-transformer';

export class LoginDto {
  @ApiProperty() @IsEmail() @Transform(({ value }) => value?.toLowerCase().trim()) email: string;
  @ApiProperty() @IsString() @IsNotEmpty() password: string;
  @ApiPropertyOptional() @IsOptional() @IsString() mfaToken?: string;
}
export class RegisterDto {
  @ApiProperty() @IsEmail() @Transform(({ value }) => value?.toLowerCase().trim()) email: string;
  @ApiProperty() @IsString() @MinLength(8) @Matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/, { message: 'Weak password' }) password: string;
  @ApiProperty() @IsString() @IsNotEmpty() firstName: string;
  @ApiProperty() @IsString() @IsNotEmpty() lastName: string;
  @ApiPropertyOptional() @IsOptional() @IsString() phone?: string;
  @ApiPropertyOptional() @IsOptional() @IsString() schoolId?: string;
}
export class RefreshTokenDto { @ApiProperty() @IsString() @IsNotEmpty() refreshToken: string; }
export class ForgotPasswordDto { @ApiProperty() @IsEmail() @Transform(({ value }) => value?.toLowerCase().trim()) email: string; }
export class ResetPasswordDto {
  @ApiProperty() @IsString() @IsNotEmpty() token: string;
  @ApiProperty() @IsString() @MinLength(8) @Matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/, { message: 'Weak password' }) password: string;
}
export class VerifyEmailDto { @ApiProperty() @IsString() @IsNotEmpty() token: string; }
export class EnableMfaDto { @ApiProperty() @IsString() @IsNotEmpty() @MinLength(6) @MaxLength(8) token: string; }
export class VerifyMfaDto { @ApiProperty() @IsString() userId: string; @ApiProperty() @IsString() token: string; }
export class ChangePasswordDto {
  @ApiProperty() @IsString() @IsNotEmpty() currentPassword: string;
  @ApiProperty() @IsString() @MinLength(8) @Matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/, { message: 'Weak password' }) newPassword: string;
}
