import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../../../database/prisma.service';
import { JwtPayload } from '../interfaces/auth.interfaces';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy, 'jwt') {
  constructor(
    private readonly config: ConfigService,
    private readonly prisma: PrismaService,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: config.get<string>('jwt.accessSecret'),
    });
  }

  async validate(payload: JwtPayload) {
    const user = await this.prisma.user.findUnique({
      where: { id: payload.sub },
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        avatar: true,
        status: true,
        schoolId: true,
        mfaEnabled: true,
        roles: {
          include: {
            role: {
              include: {
                permissions: {
                  include: { permission: true },
                },
              },
            },
          },
        },
        school: {
          select: { id: true, name: true, slug: true, isActive: true, currency: true, currencySymbol: true },
        },
      },
    });

    if (!user) throw new UnauthorizedException('User not found');
    if (user.status === 'SUSPENDED' || user.status === 'ARCHIVED') {
      throw new UnauthorizedException('Account is not active');
    }

    // Flatten permissions for easy checking
    const permissions = user.roles.flatMap((ur) =>
      ur.role.permissions.map(
        (rp) => `${rp.permission.module}:${rp.permission.resource}:${rp.permission.action}`,
      ),
    );

    const roles = user.roles.map((ur) => ur.role.slug);

    return {
      ...user,
      roles,
      permissions,
      schoolId: user.schoolId,
    };
  }
}
