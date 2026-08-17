import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Put, Post, Delete, Body, Param, Req, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';
import { DatabaseModule } from '../../database/database.module';

@Injectable()
class CustomizationService {
  constructor(private prisma: PrismaService) {}

  async getTheme(schoolId: string) {
    const theme = await this.prisma.schoolTheme.findUnique({ where: { schoolId } });
    return theme || { primaryColor: '#1a56db', secondaryColor: '#7c3aed', accentColor: '#059669', fontFamily: 'Inter' };
  }

  async updateTheme(schoolId: string, dto: {
    primaryColor?: string; secondaryColor?: string; accentColor?: string;
    fontFamily?: string; logoUrl?: string; faviconUrl?: string;
    loginBgUrl?: string; customCss?: string; footerText?: string;
  }) {
    return this.prisma.schoolTheme.upsert({
      where: { schoolId },
      create: { schoolId, ...dto },
      update: dto,
    });
  }

  async getSchoolBranding(schoolId: string) {
    const [school, theme] = await Promise.all([
      this.prisma.school.findUnique({ where: { id: schoolId }, select: { name: true, logo: true, address: true, phone: true, email: true, website: true } }),
      this.prisma.schoolTheme.findUnique({ where: { schoolId } }),
    ]);
    return { school, theme };
  }

  async updateSchoolBranding(schoolId: string, dto: any) {
    return this.prisma.school.update({ where: { id: schoolId }, data: dto });
  }

  async getCustomPages(schoolId: string) {
    return this.prisma.customPage.findMany({ where: { schoolId }, orderBy: { createdAt: 'desc' } });
  }

  async getCustomPage(schoolId: string, slug: string) {
    const page = await this.prisma.customPage.findUnique({ where: { schoolId_slug: { schoolId, slug } } });
    if (!page) throw new NotFoundException('Page not found');
    return page;
  }

  async upsertCustomPage(schoolId: string, dto: { slug: string; title: string; content: any; isPublished?: boolean }) {
    return this.prisma.customPage.upsert({
      where: { schoolId_slug: { schoolId, slug: dto.slug } },
      create: { schoolId, ...dto },
      update: dto,
    });
  }

  async deleteCustomPage(schoolId: string, slug: string) {
    return this.prisma.customPage.delete({ where: { schoolId_slug: { schoolId, slug } } });
  }
}

@Controller('customization')
@UseGuards(JwtAuthGuard, PermissionsGuard)
class CustomizationController {
  constructor(private readonly svc: CustomizationService) {}

  @Get('theme') @RequirePermissions('customization:customization:READ') getTheme(@Req() r: any) { return this.svc.getTheme(r.user.schoolId); }
  @Put('theme') @RequirePermissions('customization:customization:UPDATE') updateTheme(@Req() r: any, @Body() b: any) { return this.svc.updateTheme(r.user.schoolId, b); }
  @Get('branding') @RequirePermissions('customization:customization:READ') getBranding(@Req() r: any) { return this.svc.getSchoolBranding(r.user.schoolId); }
  @Put('branding') @RequirePermissions('customization:customization:UPDATE') updateBranding(@Req() r: any, @Body() b: any) { return this.svc.updateSchoolBranding(r.user.schoolId, b); }
  @Get('pages') @RequirePermissions('customization:customization:READ') getPages(@Req() r: any) { return this.svc.getCustomPages(r.user.schoolId); }
  @Get('pages/:slug') @RequirePermissions('customization:customization:READ') getPage(@Req() r: any, @Param('slug') slug: string) { return this.svc.getCustomPage(r.user.schoolId, slug); }
  @Put('pages/:slug') @RequirePermissions('customization:customization:UPDATE') upsertPage(@Req() r: any, @Param('slug') slug: string, @Body() b: any) { return this.svc.upsertCustomPage(r.user.schoolId, { ...b, slug }); }
  @Delete('pages/:slug') @RequirePermissions('customization:customization:DELETE') deletePage(@Req() r: any, @Param('slug') slug: string) { return this.svc.deleteCustomPage(r.user.schoolId, slug); }
}

@Module({
  imports: [DatabaseModule],
  controllers: [CustomizationController],
  providers: [CustomizationService],
  exports: [CustomizationService],
})
export class CustomizationModule {}
