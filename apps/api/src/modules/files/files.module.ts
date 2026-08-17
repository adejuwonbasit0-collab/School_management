import { Module } from '@nestjs/common';
import { Injectable, Logger } from '@nestjs/common';
import { Controller, Post, Get, Delete, Param, UploadedFile, UseInterceptors, UseGuards, Req } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard } from '../../guards/jwt-auth.guard';
import { CurrentUser, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth, ApiConsumes } from '@nestjs/swagger';
import { v2 as cloudinary } from 'cloudinary';

@Injectable()
export class FilesService {
  private readonly logger = new Logger(FilesService.name);

  constructor(private readonly config: ConfigService, private readonly prisma: PrismaService) {
    cloudinary.config({
      cloud_name: config.get('storage.cloudinary.cloudName'),
      api_key: config.get('storage.cloudinary.apiKey'),
      api_secret: config.get('storage.cloudinary.apiSecret'),
    });
  }

  async uploadFile(schoolId: string, file: Express.Multer.File, uploadedBy: string, options: any = {}) {
    try {
      const result = await new Promise<any>((resolve, reject) => {
        const stream = cloudinary.uploader.upload_stream(
          { folder: `educore/${schoolId}`, resource_type: 'auto', ...options },
          (error, result) => error ? reject(error) : resolve(result),
        );
        stream.end(file.buffer);
      });

      const doc = await this.prisma.document.create({
        data: { schoolId, name: options.name || file.originalname, type: options.type || 'GENERAL', url: result.secure_url, size: file.size, mimeType: file.mimetype, uploadedBy },
      });

      return { id: doc.id, url: result.secure_url, publicId: result.public_id, name: doc.name };
    } catch (err) {
      this.logger.error(`Upload failed: ${err.message}`);
      throw err;
    }
  }

  async deleteFile(publicId: string) {
    await cloudinary.uploader.destroy(publicId);
    return { message: 'File deleted' };
  }

  async getFiles(schoolId: string, studentId?: string) {
    return this.prisma.document.findMany({
      where: { schoolId, ...(studentId && { studentId }) },
      orderBy: { createdAt: 'desc' },
    });
  }
}

@ApiTags('Files') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard)
@Controller({ path: 'files', version: '1' })
export class FilesController {
  constructor(private readonly service: FilesService) {}

  @Post('upload')
  @ApiConsumes('multipart/form-data')
  @UseInterceptors(FileInterceptor('file', { limits: { fileSize: 50 * 1024 * 1024 } }))
  async upload(@SchoolId() sid: string, @UploadedFile() file: Express.Multer.File, @CurrentUser('id') uid: string, @Req() req: any) {
    return this.service.uploadFile(sid, file, uid, req.body);
  }

  @Get()
  getFiles(@SchoolId() sid: string) { return this.service.getFiles(sid); }

  @Delete(':publicId')
  deleteFile(@Param('publicId') id: string) { return this.service.deleteFile(id); }
}

@Module({ controllers: [FilesController], providers: [FilesService], exports: [FilesService] })
export class FilesModule {}
