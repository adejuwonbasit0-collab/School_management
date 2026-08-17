import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';

@Injectable()
export class InventoryService {
  constructor(private prisma: PrismaService) {}

  // ── Categories ────────────────────────────────────────────────────────────
  async getCategories(schoolId: string) {
    return this.prisma.inventoryCategory.findMany({
      where: { schoolId },
      include: { _count: { select: { items: true } } },
      orderBy: { name: 'asc' },
    });
  }

  async createCategory(schoolId: string, name: string) {
    return this.prisma.inventoryCategory.create({ data: { schoolId, name } });
  }

  // ── Items ─────────────────────────────────────────────────────────────────
  async getItems(schoolId: string, query: any = {}) {
    const { search, categoryId, isAsset, page = 1, limit = 20 } = query;
    const where: any = { schoolId };
    if (categoryId) where.categoryId = categoryId;
    if (isAsset !== undefined) where.isAsset = isAsset === 'true';
    if (search) where.name = { contains: search, mode: 'insensitive' };

    const [data, total] = await Promise.all([
      this.prisma.inventoryItem.findMany({
        where, skip: (page - 1) * limit, take: limit,
        include: { category: true, _count: { select: { transactions: true } } },
        orderBy: { name: 'asc' },
      }),
      this.prisma.inventoryItem.count({ where }),
    ]);
    return { data, total, page: +page, limit: +limit, pages: Math.ceil(total / limit) };
  }

  async getItem(id: string, schoolId: string) {
    const item = await this.prisma.inventoryItem.findFirst({
      where: { id, schoolId },
      include: {
        category: true,
        transactions: { orderBy: { createdAt: 'desc' }, take: 20 },
      },
    });
    if (!item) throw new NotFoundException('Item not found');
    return item;
  }

  async createItem(schoolId: string, dto: any) {
    return this.prisma.inventoryItem.create({ data: { schoolId, ...dto } });
  }

  async updateItem(id: string, schoolId: string, dto: any) {
    const item = await this.prisma.inventoryItem.findFirst({ where: { id, schoolId } });
    if (!item) throw new NotFoundException('Item not found');
    return this.prisma.inventoryItem.update({ where: { id }, data: dto });
  }

  async deleteItem(id: string, schoolId: string) {
    const item = await this.prisma.inventoryItem.findFirst({ where: { id, schoolId } });
    if (!item) throw new NotFoundException('Item not found');
    return this.prisma.inventoryItem.delete({ where: { id } });
  }

  // ── Transactions (Stock In/Out) ───────────────────────────────────────────
  async recordTransaction(itemId: string, schoolId: string, userId: string, dto: {
    type: 'IN' | 'OUT' | 'ADJUST' | 'TRANSFER';
    quantity: number;
    unitCost?: number;
    reference?: string;
    notes?: string;
  }) {
    const item = await this.prisma.inventoryItem.findFirst({ where: { id: itemId, schoolId } });
    if (!item) throw new NotFoundException('Item not found');

    const newQty = dto.type === 'IN'
      ? item.quantityInStock + dto.quantity
      : dto.type === 'OUT'
      ? item.quantityInStock - dto.quantity
      : dto.quantity; // ADJUST sets absolute quantity

    if (newQty < 0) throw new BadRequestException('Insufficient stock');

    const [tx] = await this.prisma.$transaction([
      this.prisma.inventoryTx.create({
        data: { itemId, type: dto.type, quantity: dto.quantity, unitCost: dto.unitCost, reference: dto.reference, notes: dto.notes, performedBy: userId },
      }),
      this.prisma.inventoryItem.update({ where: { id: itemId }, data: { quantityInStock: newQty } }),
    ]);
    return tx;
  }

  async getTransactions(itemId: string, schoolId: string) {
    const item = await this.prisma.inventoryItem.findFirst({ where: { id: itemId, schoolId } });
    if (!item) throw new NotFoundException('Item not found');
    return this.prisma.inventoryTx.findMany({
      where: { itemId },
      orderBy: { createdAt: 'desc' },
    });
  }

  // ── Suppliers ─────────────────────────────────────────────────────────────
  async getSuppliers(schoolId: string) {
    return this.prisma.supplier.findMany({ where: { schoolId }, orderBy: { name: 'asc' } });
  }

  async createSupplier(schoolId: string, dto: any) {
    return this.prisma.supplier.create({ data: { schoolId, ...dto } });
  }

  async updateSupplier(id: string, schoolId: string, dto: any) {
    return this.prisma.supplier.update({ where: { id }, data: dto });
  }

  // ── Low Stock Alerts ──────────────────────────────────────────────────────
  async getLowStockItems(schoolId: string) {
    return this.prisma.inventoryItem.findMany({
      where: { schoolId, quantityInStock: { lte: this.prisma.inventoryItem.fields.reorderLevel } },
      include: { category: true },
      orderBy: { quantityInStock: 'asc' },
    });
  }

  async getInventoryStats(schoolId: string) {
    const [totalItems, totalAssets, lowStock, byCategory] = await Promise.all([
      this.prisma.inventoryItem.count({ where: { schoolId, isAsset: false } }),
      this.prisma.inventoryItem.count({ where: { schoolId, isAsset: true } }),
      this.prisma.inventoryItem.count({
        where: { schoolId, quantityInStock: { lte: 5 } },
      }),
      this.prisma.inventoryItem.groupBy({
        by: ['categoryId'],
        where: { schoolId },
        _count: true,
        _sum: { quantityInStock: true },
      }),
    ]);
    return { totalItems, totalAssets, lowStock, byCategory };
  }
}
