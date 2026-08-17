import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';

@Injectable()
export class DocumentsService {
  constructor(private prisma: PrismaService) {}

  // ─── Folders ─────────────────────────────────────────────────────────────

  async getFolders(schoolId: string, parentId?: string) {
    return this.prisma.documentFolder.findMany({
      where: { schoolId, parentId: parentId || null },
      include: {
        _count: { select: { children: true, documents: true } },
      },
      orderBy: { name: 'asc' },
    });
  }

  async createFolder(schoolId: string, userId: string, dto: {
    name: string;
    description?: string;
    parentId?: string;
  }) {
    if (dto.parentId) {
      const parent = await this.prisma.documentFolder.findFirst({
        where: { id: dto.parentId, schoolId },
      });
      if (!parent) throw new NotFoundException('Parent folder not found');
    }

    return this.prisma.documentFolder.create({
      data: { schoolId, createdBy: userId, ...dto },
    });
  }

  async updateFolder(id: string, schoolId: string, dto: { name?: string; description?: string }) {
    const folder = await this.prisma.documentFolder.findFirst({ where: { id, schoolId } });
    if (!folder) throw new NotFoundException('Folder not found');
    return this.prisma.documentFolder.update({ where: { id }, data: dto });
  }

  async deleteFolder(id: string, schoolId: string) {
    const folder = await this.prisma.documentFolder.findFirst({ where: { id, schoolId } });
    if (!folder) throw new NotFoundException('Folder not found');
    const childCount = await this.prisma.documentFolder.count({ where: { parentId: id } });
    const docCount = await this.prisma.documentV2.count({ where: { folderId: id } });
    if (childCount > 0 || docCount > 0) {
      throw new ForbiddenException('Cannot delete non-empty folder. Move or delete contents first.');
    }
    return this.prisma.documentFolder.delete({ where: { id } });
  }

  // ─── Documents ────────────────────────────────────────────────────────────

  async getDocuments(schoolId: string, query: {
    folderId?: string;
    studentId?: string;
    staffId?: string;
    search?: string;
    tags?: string[];
    page?: number;
    limit?: number;
  }) {
    const { folderId, studentId, staffId, search, tags, page = 1, limit = 20 } = query;
    const skip = (page - 1) * limit;

    const where: any = { schoolId };
    if (folderId !== undefined) where.folderId = folderId || null;
    if (studentId) where.studentId = studentId;
    if (staffId) where.staffId = staffId;
    if (search) where.name = { contains: search, mode: 'insensitive' };
    if (tags?.length) where.tags = { hasSome: tags };

    const [data, total] = await Promise.all([
      this.prisma.documentV2.findMany({
        where,
        include: {
          folder: { select: { id: true, name: true } },
          _count: { select: { versions: true } },
        },
        orderBy: { createdAt: 'desc' },
        skip,
        take: limit,
      }),
      this.prisma.documentV2.count({ where }),
    ]);

    return { data, total, page, limit, pages: Math.ceil(total / limit) };
  }

  async getDocument(id: string, schoolId: string) {
    const doc = await this.prisma.documentV2.findFirst({
      where: { id, schoolId },
      include: {
        folder: true,
        versions: { orderBy: { version: 'desc' } },
      },
    });
    if (!doc) throw new NotFoundException('Document not found');
    return doc;
  }

  async createDocument(schoolId: string, userId: string, dto: {
    folderId?: string;
    studentId?: string;
    staffId?: string;
    name: string;
    description?: string;
    fileType: string;
    mimeType?: string;
    size?: number;
    url: string;
    tags?: string[];
    isPublic?: boolean;
    accessRoles?: string[];
  }) {
    return this.prisma.documentV2.create({
      data: {
        schoolId,
        uploadedBy: userId,
        version: 1,
        ...dto,
      },
      include: { folder: true },
    });
  }

  async updateDocument(id: string, schoolId: string, userId: string, dto: {
    name?: string;
    description?: string;
    folderId?: string;
    tags?: string[];
    isPublic?: boolean;
    accessRoles?: string[];
    // If new file uploaded:
    url?: string;
    size?: number;
    mimeType?: string;
    fileType?: string;
  }) {
    const doc = await this.prisma.documentV2.findFirst({ where: { id, schoolId } });
    if (!doc) throw new NotFoundException('Document not found');

    // If a new file version is provided, archive old version first
    if (dto.url && dto.url !== doc.url) {
      await this.prisma.documentVersion.create({
        data: {
          documentId: id,
          version: doc.version,
          url: doc.url,
          size: doc.size,
          uploadedBy: userId,
        },
      });
    }

    return this.prisma.documentV2.update({
      where: { id },
      data: {
        ...dto,
        ...(dto.url && dto.url !== doc.url ? { version: doc.version + 1 } : {}),
      },
      include: { folder: true, versions: { orderBy: { version: 'desc' } } },
    });
  }

  async deleteDocument(id: string, schoolId: string) {
    const doc = await this.prisma.documentV2.findFirst({ where: { id, schoolId } });
    if (!doc) throw new NotFoundException('Document not found');
    return this.prisma.documentV2.delete({ where: { id } });
  }

  async moveDocument(id: string, schoolId: string, folderId: string | null) {
    if (folderId) {
      const folder = await this.prisma.documentFolder.findFirst({ where: { id: folderId, schoolId } });
      if (!folder) throw new NotFoundException('Target folder not found');
    }
    const doc = await this.prisma.documentV2.findFirst({ where: { id, schoolId } });
    if (!doc) throw new NotFoundException('Document not found');
    return this.prisma.documentV2.update({ where: { id }, data: { folderId } });
  }

  async getDocumentStats(schoolId: string) {
    const [totalDocs, totalFolders, byType] = await Promise.all([
      this.prisma.documentV2.count({ where: { schoolId } }),
      this.prisma.documentFolder.count({ where: { schoolId } }),
      this.prisma.documentV2.groupBy({
        by: ['fileType'],
        where: { schoolId },
        _count: true,
        _sum: { size: true },
      }),
    ]);

    return {
      totalDocuments: totalDocs,
      totalFolders,
      byType: byType.map(b => ({
        type: b.fileType,
        count: b._count,
        totalSize: b._sum.size || 0,
      })),
    };
  }
}
