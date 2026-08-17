import { Module } from '@nestjs/common';
import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { Controller, Delete, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class LibraryService {
  constructor(private readonly prisma: PrismaService) {}

  async getLibrary(schoolId: string) {
    return this.prisma.library.findUnique({ where: { schoolId }, include: { _count: { select: { items: true } } } });
  }

  async getItems(schoolId: string, query: any = {}) {
    const { page = 1, limit = 20, search, category } = query;
    const library = await this.prisma.library.findUnique({ where: { schoolId } });
    if (!library) return { data: [], meta: { total: 0, page, limit, totalPages: 0 } };
    const where: any = { libraryId: library.id, ...(search && { OR: [{ title: { contains: search, mode: 'insensitive' } }, { author: { contains: search, mode: 'insensitive' } }, { isbn: { contains: search, mode: 'insensitive' } }] }), ...(category && { category }) };
    const [data, total] = await Promise.all([
      this.prisma.libraryItem.findMany({ where, skip: (page-1)*limit, take: limit, include: { _count: { select: { borrows: true } } }, orderBy: { title: 'asc' } }),
      this.prisma.libraryItem.count({ where }),
    ]);
    return { data, meta: { total, page, limit, totalPages: Math.ceil(total/limit) } };
  }

  async addItem(schoolId: string, data: any) {
    const library = await this.prisma.library.findUnique({ where: { schoolId } });
    if (!library) throw new NotFoundException('Library not found');
    return this.prisma.libraryItem.create({ data: { libraryId: library.id, title: data.title, author: data.author, isbn: data.isbn, category: data.category, publisher: data.publisher, year: data.year, quantity: data.quantity || 1, available: data.quantity || 1, description: data.description } });
  }


  async deleteItem(schoolId: string, id: string) {
    const item = await this.prisma.libraryItem.findFirst({ where: { id, schoolId } });
    if (!item) throw new Error('Book not found');
    return this.prisma.libraryItem.delete({ where: { id } });
  }

  async getBorrowings(schoolId: string, query: any = {}) {
    const { status, page = 1, limit = 20 } = query;
    const where: any = { item: { schoolId } };
    if (status === 'BORROWED' || status === 'ACTIVE') where.returnedAt = null;
    if (status === 'RETURNED') where.returnedAt = { not: null };
    if (status === 'OVERDUE') { where.returnedAt = null; where.dueDate = { lt: new Date() }; }

    const [data, total] = await Promise.all([
      this.prisma.libraryBorrow.findMany({
        where, skip: (page-1)*limit, take: limit,
        include: {
          item: { select: { title: true, author: true } },
          student: { include: { user: { select: { firstName: true, lastName: true } } } },
        },
        orderBy: { borrowedAt: 'desc' },
      }),
      this.prisma.libraryBorrow.count({ where }),
    ]);
    return { data, total };
  }

  async getLibraryStats(schoolId: string) {
    const [totalBooks, borrowed, overdue] = await Promise.all([
      this.prisma.libraryItem.count({ where: { schoolId } }),
      this.prisma.libraryBorrow.count({ where: { item: { schoolId }, returnedAt: null } }),
      this.prisma.libraryBorrow.count({ where: { item: { schoolId }, returnedAt: null, dueDate: { lt: new Date() } } }),
    ]);
    const available = await this.prisma.libraryItem.aggregate({ where: { schoolId }, _sum: { available: true } });
    return { totalBooks, borrowed, overdue, available: available._sum.available || 0 };
  }

  async borrowBook(schoolId: string, data: any) {
    const item = await this.prisma.libraryItem.findFirst({ where: { id: data.itemId, library: { schoolId } } });
    if (!item) throw new NotFoundException('Book not found');
    if (item.available < 1) throw new BadRequestException('No copies available');
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + (data.days || 14));
    const [borrow] = await this.prisma.$transaction([
      this.prisma.libraryBorrow.create({ data: { studentId: data.studentId, itemId: data.itemId, dueDate, notes: data.notes } }),
      this.prisma.libraryItem.update({ where: { id: data.itemId }, data: { available: { decrement: 1 } } }),
    ]);
    return borrow;
  }

  async returnBook(borrowId: string) {
    const borrow = await this.prisma.libraryBorrow.findUnique({ where: { id: borrowId } });
    if (!borrow || borrow.returnedAt) throw new BadRequestException('Invalid return');
    const overdueDays = Math.max(0, Math.floor((Date.now() - borrow.dueDate.getTime()) / 86400000));
    const fine = overdueDays > 0 ? overdueDays * 50 : 0;
    const [updated] = await this.prisma.$transaction([
      this.prisma.libraryBorrow.update({ where: { id: borrowId }, data: { returnedAt: new Date(), fine } }),
      this.prisma.libraryItem.update({ where: { id: borrow.itemId }, data: { available: { increment: 1 } } }),
    ]);
    return { ...updated, fine };
  }

  async getActiveBorrows(schoolId: string) {
    const library = await this.prisma.library.findUnique({ where: { schoolId } });
    if (!library) return [];
    return this.prisma.libraryBorrow.findMany({
      where: { returnedAt: null, item: { libraryId: library.id } },
      include: { student: { include: { user: { select: { firstName: true, lastName: true } } } }, item: { select: { title: true, author: true } } },
      orderBy: { dueDate: 'asc' },
    });
  }
}

@ApiTags('Library') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'library', version: '1' })
export class LibraryController {
  constructor(private readonly service: LibraryService) {}

  @Get('books') @RequirePermissions('library:library:READ') getBooks(@SchoolId() sid: string, @Query() q: any) { return this.service.getItems(sid, q); }
  @Post('books') @RequirePermissions('library:library:CREATE') addBook(@SchoolId() sid: string, @Body() d: any) { return this.service.addItem(sid, d); }
  @Delete('books/:id') @RequirePermissions('library:library:UPDATE') deleteBook(@SchoolId() sid: string, @Param('id') id: string) { return this.service.deleteItem(sid, id); }
  @Get('borrowings') @RequirePermissions('library:library:READ') getBorrowings(@SchoolId() sid: string, @Query() q: any) { return this.service.getBorrowings(sid, q); }
  @Post('borrowings') @RequirePermissions('library:library:CREATE') issueBorrow(@SchoolId() sid: string, @Body() d: any) { return this.service.borrowBook(sid, { itemId: d.bookId, studentId: d.studentId, dueDate: d.dueDate, notes: d.notes }); }
  @Put('borrowings/:id/return') @RequirePermissions('library:library:UPDATE') returnBorrow(@Param('id') id: string) { return this.service.returnBook(id); }
  @Get('stats') @RequirePermissions('library:library:READ') getStats(@SchoolId() sid: string) { return this.service.getLibraryStats(sid); }

  @Get() @RequirePermissions('library:library:READ') getLibrary(@SchoolId() sid: string) { return this.service.getLibrary(sid); }
  @Get('items') @RequirePermissions('library:library:READ') getItems(@SchoolId() sid: string, @Query() q: any) { return this.service.getItems(sid, q); }
  @Post('items') @RequirePermissions('library:library:CREATE') addItem(@SchoolId() sid: string, @Body() d: any) { return this.service.addItem(sid, d); }
  @Post('borrow') @RequirePermissions('library:library:CREATE') borrowBook(@SchoolId() sid: string, @Body() d: any) { return this.service.borrowBook(sid, d); }
  @Put('borrow/:id/return') @RequirePermissions('library:library:UPDATE') returnBook(@Param('id') id: string) { return this.service.returnBook(id); }
  @Get('borrows/active') @RequirePermissions('library:library:READ') getActiveBorrows(@SchoolId() sid: string) { return this.service.getActiveBorrows(sid); }
}

@Module({ controllers: [LibraryController], providers: [LibraryService], exports: [LibraryService] })
export class LibraryModule {}
