import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId, CurrentUser } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class CmsService {
  constructor(private readonly prisma: PrismaService) {}

  // Events
  async getEvents(schoolId: string, query: any = {}) {
    return this.prisma.event.findMany({ where: { schoolId }, orderBy: { startDate: 'asc' } });
  }
  async createEvent(schoolId: string, data: any, createdBy: string) {
    return this.prisma.event.create({ data: { schoolId, title: data.title, description: data.description, startDate: new Date(data.startDate), endDate: data.endDate ? new Date(data.endDate) : undefined, location: data.location, image: data.image, isPublic: data.isPublic ?? true, createdBy } });
  }

  // News
  async getNews(schoolId: string, query: any = {}) {
    const { page = 1, limit = 10 } = query;
    const [data, total] = await Promise.all([
      this.prisma.newsItem.findMany({ where: { schoolId }, skip: (page-1)*limit, take: limit, orderBy: { createdAt: 'desc' } }),
      this.prisma.newsItem.count({ where: { schoolId } }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }
  async createNews(schoolId: string, data: any, createdBy: string) {
    const slug = data.title.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') + '-' + Date.now();
    return this.prisma.newsItem.create({ data: { schoolId, title: data.title, slug, excerpt: data.excerpt, content: data.content, image: data.image, tags: data.tags || [], isPublished: data.isPublished || false, publishedAt: data.isPublished ? new Date() : undefined, createdBy } });
  }
  async updateNews(id: string, data: any) {
    return this.prisma.newsItem.update({ where: { id }, data: { title: data.title, content: data.content, excerpt: data.excerpt, image: data.image, tags: data.tags, isPublished: data.isPublished, publishedAt: data.isPublished ? new Date() : undefined } });
  }

  // Pages
  async getPages(schoolId: string) { return this.prisma.page.findMany({ where: { schoolId } }); }
  async createPage(schoolId: string, data: any) {
    const slug = data.slug || data.title.toLowerCase().replace(/\s+/g, '-');
    return this.prisma.page.create({ data: { schoolId, title: data.title, slug, content: data.content || {}, isPublished: data.isPublished || false, seoTitle: data.seoTitle, seoDesc: data.seoDesc } });
  }
  async updatePage(id: string, data: any) {
    return this.prisma.page.update({ where: { id }, data: { title: data.title, content: data.content, isPublished: data.isPublished, seoTitle: data.seoTitle, seoDesc: data.seoDesc } });
  }

  // Menus
  async getMenus(schoolId: string, location?: string) {
    return this.prisma.menuItem.findMany({ where: { schoolId, parentId: null, ...(location && { location }), isActive: true }, include: { children: { where: { isActive: true }, orderBy: { order: 'asc' } } }, orderBy: { order: 'asc' } });
  }
}

@ApiTags('CMS') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'cms', version: '1' })
export class CmsController {
  constructor(private readonly service: CmsService) {}
  @Get('events') getEvents(@SchoolId() sid: string) { return this.service.getEvents(sid); }
  @Post('events') @RequirePermissions('cms:events:CREATE') createEvent(@SchoolId() sid: string, @Body() d: any, @CurrentUser('id') uid: string) { return this.service.createEvent(sid, d, uid); }
  @Get('news') getNews(@SchoolId() sid: string, @Query() q: any) { return this.service.getNews(sid, q); }
  @Post('news') @RequirePermissions('cms:news:CREATE') createNews(@SchoolId() sid: string, @Body() d: any, @CurrentUser('id') uid: string) { return this.service.createNews(sid, d, uid); }
  @Put('news/:id') @RequirePermissions('cms:news:UPDATE') updateNews(@Param('id') id: string, @Body() d: any) { return this.service.updateNews(id, d); }
  @Get('pages') getPages(@SchoolId() sid: string) { return this.service.getPages(sid); }
  @Post('pages') @RequirePermissions('cms:pages:CREATE') createPage(@SchoolId() sid: string, @Body() d: any) { return this.service.createPage(sid, d); }
  @Put('pages/:id') @RequirePermissions('cms:pages:UPDATE') updatePage(@Param('id') id: string, @Body() d: any) { return this.service.updatePage(id, d); }
  @Get('menus') getMenus(@SchoolId() sid: string, @Query('location') loc?: string) { return this.service.getMenus(sid, loc); }
}

@Module({ controllers: [CmsController], providers: [CmsService], exports: [CmsService] })
export class CmsModule {}
