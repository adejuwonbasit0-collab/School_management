import { Controller, Get, Post, Put, Patch, Delete, Body, Param, Query, Req, UseGuards } from '@nestjs/common';
import { DocumentsService } from './documents.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';

@Controller('documents')
@UseGuards(JwtAuthGuard, PermissionsGuard)
export class DocumentsController {
  constructor(private readonly documentsService: DocumentsService) {}

  // ── Stats ──────────────────────────────────────────────────────────────

  @Get('stats') @RequirePermissions('documents:documents:READ')
  getStats(@Req() req: any) {
    return this.documentsService.getDocumentStats(req.user.schoolId);
  }

  // ── Folders ────────────────────────────────────────────────────────────

  @Get('folders') @RequirePermissions('documents:documents:READ')
  getFolders(@Req() req: any, @Query('parentId') parentId?: string) {
    return this.documentsService.getFolders(req.user.schoolId, parentId);
  }

  @Post('folders') @RequirePermissions('documents:documents:CREATE')
  createFolder(@Req() req: any, @Body() dto: any) {
    return this.documentsService.createFolder(req.user.schoolId, req.user.id, dto);
  }

  @Put('folders/:id') @RequirePermissions('documents:documents:UPDATE')
  updateFolder(@Param('id') id: string, @Req() req: any, @Body() dto: any) {
    return this.documentsService.updateFolder(id, req.user.schoolId, dto);
  }

  @Delete('folders/:id') @RequirePermissions('documents:documents:DELETE')
  deleteFolder(@Param('id') id: string, @Req() req: any) {
    return this.documentsService.deleteFolder(id, req.user.schoolId);
  }

  // ── Documents ──────────────────────────────────────────────────────────

  @Get() @RequirePermissions('documents:documents:READ')
  getDocuments(@Req() req: any, @Query() query: any) {
    return this.documentsService.getDocuments(req.user.schoolId, {
      folderId: query.folderId,
      studentId: query.studentId,
      staffId: query.staffId,
      search: query.search,
      tags: query.tags ? query.tags.split(',') : undefined,
      page: query.page ? parseInt(query.page) : 1,
      limit: query.limit ? parseInt(query.limit) : 20,
    });
  }

  @Get(':id') @RequirePermissions('documents:documents:READ')
  getDocument(@Param('id') id: string, @Req() req: any) {
    return this.documentsService.getDocument(id, req.user.schoolId);
  }

  @Post() @RequirePermissions('documents:documents:CREATE')
  createDocument(@Req() req: any, @Body() dto: any) {
    return this.documentsService.createDocument(req.user.schoolId, req.user.id, dto);
  }

  @Put(':id') @RequirePermissions('documents:documents:UPDATE')
  updateDocument(@Param('id') id: string, @Req() req: any, @Body() dto: any) {
    return this.documentsService.updateDocument(id, req.user.schoolId, req.user.id, dto);
  }

  @Patch(':id/move') @RequirePermissions('documents:documents:UPDATE')
  moveDocument(@Param('id') id: string, @Req() req: any, @Body() body: { folderId: string | null }) {
    return this.documentsService.moveDocument(id, req.user.schoolId, body.folderId);
  }

  @Delete(':id') @RequirePermissions('documents:documents:DELETE')
  deleteDocument(@Param('id') id: string, @Req() req: any) {
    return this.documentsService.deleteDocument(id, req.user.schoolId);
  }
}
