import {
  Injectable,
  UnauthorizedException,
  BadRequestException,
  ConflictException,
  ForbiddenException,
  NotFoundException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { EventEmitter2 } from '@nestjs/event-emitter';
import * as bcrypt from 'bcryptjs';
import * as speakeasy from 'speakeasy';
import * as qrcode from 'qrcode';
import { v4 as uuidv4 } from 'uuid';
import { PrismaService } from '../../database/prisma.service';
import { UsersService } from '../users/users.service';
import {
  LoginDto,
  RegisterDto,
  RefreshTokenDto,
  ForgotPasswordDto,
  ResetPasswordDto,
  VerifyEmailDto,
  EnableMfaDto,
  VerifyMfaDto,
  ChangePasswordDto,
} from './dto';
import { JwtPayload, AuthTokens } from './interfaces/auth.interfaces';

@Injectable()
export class AuthService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly jwtService: JwtService,
    private readonly config: ConfigService,
    private readonly usersService: UsersService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  // ─── Validate User (Local Strategy) ─────────────────────────────────────────
  async validateUser(email: string, password: string) {
    const user = await this.prisma.user.findUnique({
      where: { email: email.toLowerCase() },
      include: {
        roles: {
          include: {
            role: {
              include: {
                permissions: { include: { permission: true } },
              },
            },
          },
        },
        school: { select: { id: true, name: true, slug: true, isActive: true } },
      },
    });

    if (!user) throw new UnauthorizedException('Invalid credentials');
    if (user.status === 'SUSPENDED') throw new ForbiddenException('Account suspended');
    if (user.status === 'ARCHIVED') throw new ForbiddenException('Account archived');

    const isPasswordValid = await bcrypt.compare(password, user.passwordHash);
    if (!isPasswordValid) throw new UnauthorizedException('Invalid credentials');

    return user;
  }

  // ─── Login ───────────────────────────────────────────────────────────────────
  async login(dto: LoginDto, ipAddress: string, userAgent: string) {
    const user = await this.validateUser(dto.email, dto.password);

    // MFA check
    if (user.mfaEnabled) {
      if (!dto.mfaToken) {
        return { requiresMfa: true, userId: user.id };
      }
      await this.verifyMfaToken(user.id, dto.mfaToken);
    }

    if (user.status === 'PENDING_VERIFICATION') {
      throw new ForbiddenException('Please verify your email before logging in');
    }

    // Update last login
    await this.prisma.user.update({
      where: { id: user.id },
      data: { lastLogin: new Date(), lastLoginIp: ipAddress },
    });

    const tokens = await this.generateTokens(user, ipAddress, userAgent);

    this.eventEmitter.emit('auth.login', {
      userId: user.id,
      schoolId: user.schoolId,
      ipAddress,
      userAgent,
    });

    return {
      tokens,
      user: this.sanitizeUser(user),
    };
  }

  // ─── Register ────────────────────────────────────────────────────────────────
  async register(dto: RegisterDto) {
    const existingUser = await this.prisma.user.findUnique({
      where: { email: dto.email.toLowerCase() },
    });

    if (existingUser) throw new ConflictException('Email already registered');

    const passwordHash = await bcrypt.hash(dto.password, 12);
    const verificationToken = uuidv4();

    const user = await this.prisma.user.create({
      data: {
        email: dto.email.toLowerCase(),
        passwordHash,
        firstName: dto.firstName,
        lastName: dto.lastName,
        phone: dto.phone,
        status: 'PENDING_VERIFICATION',
        schoolId: dto.schoolId,
      },
    });

    // Store verification token
    await this.prisma.passwordReset.create({
      data: {
        userId: user.id,
        token: verificationToken,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24h
      },
    });

    this.eventEmitter.emit('auth.registered', {
      userId: user.id,
      email: user.email,
      firstName: user.firstName,
      verificationToken,
    });

    return {
      message: 'Registration successful. Please verify your email.',
      userId: user.id,
    };
  }

  // ─── Verify Email ────────────────────────────────────────────────────────────
  async verifyEmail(dto: VerifyEmailDto) {
    const record = await this.prisma.passwordReset.findFirst({
      where: {
        token: dto.token,
        usedAt: null,
        expiresAt: { gt: new Date() },
      },
      include: { user: true },
    });

    if (!record) throw new BadRequestException('Invalid or expired verification link');

    await this.prisma.$transaction([
      this.prisma.user.update({
        where: { id: record.userId },
        data: { emailVerified: true, emailVerifiedAt: new Date(), status: 'ACTIVE' },
      }),
      this.prisma.passwordReset.update({
        where: { id: record.id },
        data: { usedAt: new Date() },
      }),
    ]);

    return { message: 'Email verified successfully' };
  }

  // ─── Refresh Tokens ──────────────────────────────────────────────────────────
  async refreshTokens(dto: RefreshTokenDto, ipAddress: string, userAgent: string) {
    const tokenRecord = await this.prisma.refreshToken.findUnique({
      where: { token: dto.refreshToken },
      include: {
        user: {
          include: {
            roles: { include: { role: { include: { permissions: { include: { permission: true } } } } } },
            school: { select: { id: true, name: true, slug: true } },
          },
        },
      },
    });

    if (!tokenRecord || tokenRecord.isRevoked || tokenRecord.expiresAt < new Date()) {
      throw new UnauthorizedException('Invalid or expired refresh token');
    }

    // Rotate token
    await this.prisma.refreshToken.update({
      where: { id: tokenRecord.id },
      data: { isRevoked: true },
    });

    const tokens = await this.generateTokens(tokenRecord.user, ipAddress, userAgent);
    return { tokens, user: this.sanitizeUser(tokenRecord.user) };
  }

  // ─── Logout ──────────────────────────────────────────────────────────────────
  async logout(userId: string, refreshToken?: string) {
    if (refreshToken) {
      await this.prisma.refreshToken.updateMany({
        where: { userId, token: refreshToken },
        data: { isRevoked: true },
      });
    } else {
      // Revoke all sessions
      await this.prisma.refreshToken.updateMany({
        where: { userId },
        data: { isRevoked: true },
      });
    }
    return { message: 'Logged out successfully' };
  }

  // ─── Forgot Password ─────────────────────────────────────────────────────────
  async forgotPassword(dto: ForgotPasswordDto) {
    const user = await this.prisma.user.findUnique({
      where: { email: dto.email.toLowerCase() },
    });

    // Always return success to prevent email enumeration
    if (!user) return { message: 'If that email exists, a reset link has been sent' };

    const token = uuidv4();
    await this.prisma.passwordReset.create({
      data: {
        userId: user.id,
        token,
        expiresAt: new Date(Date.now() + 1 * 60 * 60 * 1000), // 1h
      },
    });

    this.eventEmitter.emit('auth.forgotPassword', {
      userId: user.id,
      email: user.email,
      firstName: user.firstName,
      token,
    });

    return { message: 'If that email exists, a reset link has been sent' };
  }

  // ─── Reset Password ──────────────────────────────────────────────────────────
  async resetPassword(dto: ResetPasswordDto) {
    const record = await this.prisma.passwordReset.findFirst({
      where: {
        token: dto.token,
        usedAt: null,
        expiresAt: { gt: new Date() },
      },
    });

    if (!record) throw new BadRequestException('Invalid or expired reset link');

    const passwordHash = await bcrypt.hash(dto.password, 12);

    await this.prisma.$transaction([
      this.prisma.user.update({
        where: { id: record.userId },
        data: { passwordHash },
      }),
      this.prisma.passwordReset.update({
        where: { id: record.id },
        data: { usedAt: new Date() },
      }),
      // Revoke all refresh tokens
      this.prisma.refreshToken.updateMany({
        where: { userId: record.userId },
        data: { isRevoked: true },
      }),
    ]);

    return { message: 'Password reset successful' };
  }

  // ─── Change Password ─────────────────────────────────────────────────────────
  async changePassword(userId: string, dto: ChangePasswordDto) {
    const user = await this.prisma.user.findUnique({ where: { id: userId } });
    if (!user) throw new NotFoundException('User not found');

    const isValid = await bcrypt.compare(dto.currentPassword, user.passwordHash);
    if (!isValid) throw new BadRequestException('Current password is incorrect');

    const passwordHash = await bcrypt.hash(dto.newPassword, 12);
    await this.prisma.user.update({
      where: { id: userId },
      data: { passwordHash },
    });

    // Revoke all other sessions
    await this.prisma.refreshToken.updateMany({
      where: { userId },
      data: { isRevoked: true },
    });

    return { message: 'Password changed successfully' };
  }

  // ─── MFA Setup ───────────────────────────────────────────────────────────────
  async setupMfa(userId: string) {
    const user = await this.prisma.user.findUnique({ where: { id: userId } });
    if (!user) throw new NotFoundException('User not found');
    if (user.mfaEnabled) throw new BadRequestException('MFA is already enabled');

    const secret = speakeasy.generateSecret({
      name: `EduCore (${user.email})`,
      length: 32,
    });

    // Temporarily store secret (not enabled yet until verified)
    await this.prisma.user.update({
      where: { id: userId },
      data: { mfaSecret: secret.base32 },
    });

    const qrCodeUrl = await qrcode.toDataURL(secret.otpauth_url);

    return {
      secret: secret.base32,
      qrCode: qrCodeUrl,
      manualEntry: secret.base32,
    };
  }

  // ─── Enable MFA ──────────────────────────────────────────────────────────────
  async enableMfa(userId: string, dto: EnableMfaDto) {
    const user = await this.prisma.user.findUnique({ where: { id: userId } });
    if (!user || !user.mfaSecret) throw new BadRequestException('MFA setup not initiated');

    const isValid = speakeasy.totp.verify({
      secret: user.mfaSecret,
      encoding: 'base32',
      token: dto.token,
      window: 2,
    });

    if (!isValid) throw new BadRequestException('Invalid MFA token');

    const backupCodes = Array.from({ length: 10 }, () =>
      Math.random().toString(36).substring(2, 10).toUpperCase(),
    );

    await this.prisma.user.update({
      where: { id: userId },
      data: { mfaEnabled: true, mfaBackupCodes: backupCodes },
    });

    return { message: 'MFA enabled successfully', backupCodes };
  }

  // ─── Disable MFA ─────────────────────────────────────────────────────────────
  async disableMfa(userId: string, password: string) {
    const user = await this.prisma.user.findUnique({ where: { id: userId } });
    if (!user) throw new NotFoundException('User not found');

    const isValid = await bcrypt.compare(password, user.passwordHash);
    if (!isValid) throw new BadRequestException('Invalid password');

    await this.prisma.user.update({
      where: { id: userId },
      data: { mfaEnabled: false, mfaSecret: null, mfaBackupCodes: [] },
    });

    return { message: 'MFA disabled successfully' };
  }

  // ─── Verify MFA Token ────────────────────────────────────────────────────────
  async verifyMfaToken(userId: string, token: string) {
    const user = await this.prisma.user.findUnique({ where: { id: userId } });
    if (!user || !user.mfaSecret) throw new BadRequestException('MFA not set up');

    const isValid = speakeasy.totp.verify({
      secret: user.mfaSecret,
      encoding: 'base32',
      token,
      window: 2,
    });

    if (!isValid) {
      // Check backup codes
      if (user.mfaBackupCodes.includes(token)) {
        const updatedCodes = user.mfaBackupCodes.filter((c) => c !== token);
        await this.prisma.user.update({
          where: { id: userId },
          data: { mfaBackupCodes: updatedCodes },
        });
        return true;
      }
      throw new UnauthorizedException('Invalid MFA token');
    }

    return true;
  }

  // ─── Get Sessions ────────────────────────────────────────────────────────────
  async getSessions(userId: string) {
    return this.prisma.refreshToken.findMany({
      where: { userId, isRevoked: false, expiresAt: { gt: new Date() } },
      select: {
        id: true,
        userAgent: true,
        ipAddress: true,
        createdAt: true,
        expiresAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  // ─── Revoke Session ──────────────────────────────────────────────────────────
  async revokeSession(userId: string, sessionId: string) {
    const session = await this.prisma.refreshToken.findFirst({
      where: { id: sessionId, userId },
    });
    if (!session) throw new NotFoundException('Session not found');

    await this.prisma.refreshToken.update({
      where: { id: sessionId },
      data: { isRevoked: true },
    });

    return { message: 'Session revoked' };
  }

  // ─── Private Helpers ─────────────────────────────────────────────────────────
  private async generateTokens(user: any, ipAddress: string, userAgent: string): Promise<AuthTokens> {
    const permissions = user.roles?.flatMap((ur: any) =>
      ur.role.permissions.map((rp: any) => `${rp.permission.module}:${rp.permission.resource}:${rp.permission.action}`),
    ) || [];

    const roleNames = user.roles?.map((ur: any) => ur.role.slug) || [];

    const payload: JwtPayload = {
      sub: user.id,
      email: user.email,
      schoolId: user.schoolId,
      roles: roleNames,
      permissions,
    };

    const [accessToken, refreshTokenValue] = await Promise.all([
      this.jwtService.signAsync(payload, {
        secret: this.config.get('jwt.accessSecret'),
        expiresIn: this.config.get('jwt.accessExpiresIn', '15m'),
      }),
      this.jwtService.signAsync(
        { sub: user.id },
        {
          secret: this.config.get('jwt.refreshSecret'),
          expiresIn: this.config.get('jwt.refreshExpiresIn', '7d'),
        },
      ),
    ]);

    // Store refresh token
    await this.prisma.refreshToken.create({
      data: {
        userId: user.id,
        token: refreshTokenValue,
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
        userAgent,
        ipAddress,
      },
    });

    return { accessToken, refreshToken: refreshTokenValue };
  }

  private sanitizeUser(user: any) {
    const { passwordHash, mfaSecret, mfaBackupCodes, roles, ...safe } = user;

    const permissions = (roles ?? []).flatMap((ur: any) =>
      ur.role.permissions.map(
        (rp: any) => `${rp.permission.module}:${rp.permission.resource}:${rp.permission.action}`,
      ),
    );
    const roleSlugs = (roles ?? []).map((ur: any) => ur.role.slug);

    return { ...safe, roles: roleSlugs, permissions };
  }
}
