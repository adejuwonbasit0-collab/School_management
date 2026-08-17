import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class UsersService {
  constructor(private readonly prisma: PrismaService) {}

  async findById(id: string) {
    const user = await this.prisma.user.findUnique({
      where: { id },
      include: { roles: { include: { role: { include: { permissions: { include: { permission: true } } } } } }, school: { select: { id: true, name: true, slug: true, currency: true, currencySymbol: true, logo: true } } },
    });
    if (!user) throw new NotFoundException('User not found');
    const { passwordHash, mfaSecret, mfaBackupCodes, ...safe } = user as any;
    return { ...safe, roles: user.roles.map(r => r.role.slug), permissions: user.roles.flatMap(r => r.role.permissions.map(p => `${p.permission.module}:${p.permission.resource}:${p.permission.action}`)) };
  }

  async updateProfile(id: string, data: any) {
    await this.prisma.user.update({ where: { id }, data: { firstName: data.firstName, lastName: data.lastName, phone: data.phone, avatar: data.avatar, address: data.address, city: data.city, state: data.state } });
    return this.findById(id);
  }

  async getUsers(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20, search, roleSlug } = query;
    const where: any = { schoolId, ...(search && { OR: [{ firstName: { contains: search, mode: 'insensitive' } }, { lastName: { contains: search, mode: 'insensitive' } }, { email: { contains: search, mode: 'insensitive' } }] }) };
    const [data, total] = await Promise.all([
      this.prisma.user.findMany({ where, skip: (page-1)*limit, take: limit, select: { id: true, firstName: true, lastName: true, email: true, avatar: true, status: true, lastLogin: true, roles: { include: { role: { select: { name: true, slug: true, color: true } } } } }, orderBy: { createdAt: 'desc' } }),
      this.prisma.user.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }
}

@ApiTags('Users') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard)
@Controller({ path: 'users', version: '1' })
export class UsersController {
  constructor(private readonly service: UsersService) {}
  @Get('me') getMe(@CurrentUser() user: any) { return this.service.findById(user.id); }
  @Put('me') updateProfile(@CurrentUser('id') id: string, @Body() d: any) { return this.service.updateProfile(id, d); }
  @Get() getUsers(@SchoolId() sid: string, @Query() q: any) { return this.service.getUsers(sid, q); }
  @Get(':id') getUser(@Param('id') id: string) { return this.service.findById(id); }
}

@Module({ controllers: [UsersController], providers: [UsersService], exports: [UsersService] })
export class UsersModule {}
