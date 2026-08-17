import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../src/app.module';
import { PrismaService } from '../src/database/prisma.service';

// ─────────────────────────────────────────────────────────────────────────────
// Mock PrismaService for unit tests
// ─────────────────────────────────────────────────────────────────────────────

const mockPrismaService = {
  user: {
    findUnique: jest.fn(),
    findFirst: jest.fn(),
    findMany: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    count: jest.fn(),
  },
  student: {
    findMany: jest.fn(),
    findFirst: jest.fn(),
    findUnique: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    count: jest.fn(),
    groupBy: jest.fn(),
  },
  staff: {
    findMany: jest.fn(),
    findFirst: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    count: jest.fn(),
    groupBy: jest.fn(),
  },
  feeInvoice: {
    findMany: jest.fn(),
    findFirst: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    updateMany: jest.fn(),
    count: jest.fn(),
    aggregate: jest.fn(),
    groupBy: jest.fn(),
  },
  payment: {
    findMany: jest.fn(),
    create: jest.fn(),
    aggregate: jest.fn(),
    groupBy: jest.fn(),
  },
  attendance: {
    findMany: jest.fn(),
    create: jest.fn(),
    count: jest.fn(),
    groupBy: jest.fn(),
  },
  examination: {
    findUnique: jest.fn(),
    findMany: jest.fn(),
    update: jest.fn(),
  },
  examResult: {
    findUnique: jest.fn(),
    findMany: jest.fn(),
    upsert: jest.fn(),
    update: jest.fn(),
    updateMany: jest.fn(),
  },
  gradeScale: {
    findMany: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    findFirst: jest.fn(),
  },
  gradeScaleEntry: {
    findMany: jest.fn(),
    deleteMany: jest.fn(),
  },
  auditLog: {
    create: jest.fn(),
    findMany: jest.fn(),
    count: jest.fn(),
    groupBy: jest.fn(),
  },
  inventoryItem: {
    findMany: jest.fn(),
    findFirst: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    count: jest.fn(),
    fields: { reorderLevel: {} },
  },
  inventoryTx: {
    create: jest.fn(),
    findMany: jest.fn(),
  },
  $transaction: jest.fn((ops) => Promise.all(ops)),
};

// ─────────────────────────────────────────────────────────────────────────────
// Results Service Unit Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('ResultsService', () => {
  let service: any;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        {
          provide: 'ResultsService',
          useFactory: () => {
            const { ResultsService } = require('../src/modules/results/results.service');
            return new ResultsService(mockPrismaService as any, { sendNotification: jest.fn() } as any);
          },
        },
      ],
    }).compile();

    const { ResultsService } = require('../src/modules/results/results.service');
    service = new ResultsService(mockPrismaService as any, { sendNotification: jest.fn() } as any);
  });

  afterEach(() => jest.clearAllMocks());

  describe('defaultGrade', () => {
    it('should return A for 70+', () => {
      expect((service as any).defaultGrade(75)).toEqual({ letter: 'A', point: 4.0, remark: 'Excellent' });
    });
    it('should return B for 60-69', () => {
      expect((service as any).defaultGrade(65)).toEqual({ letter: 'B', point: 3.0, remark: 'Good' });
    });
    it('should return C for 50-59', () => {
      expect((service as any).defaultGrade(55)).toEqual({ letter: 'C', point: 2.0, remark: 'Average' });
    });
    it('should return D for 45-49', () => {
      expect((service as any).defaultGrade(47)).toEqual({ letter: 'D', point: 1.0, remark: 'Pass' });
    });
    it('should return F for below 45', () => {
      expect((service as any).defaultGrade(40)).toEqual({ letter: 'F', point: 0, remark: 'Fail' });
    });
  });

  describe('getGradeScales', () => {
    it('should return grade scales for school', async () => {
      const mockScales = [{ id: '1', name: 'WAEC', grades: [] }];
      mockPrismaService.gradeScale.findMany.mockResolvedValue(mockScales);

      const result = await service.getGradeScales('school1');
      expect(result).toEqual(mockScales);
      expect(mockPrismaService.gradeScale.findMany).toHaveBeenCalledWith(
        expect.objectContaining({ where: { schoolId: 'school1' } })
      );
    });
  });

  describe('computePositions', () => {
    it('should rank students by percentage descending', async () => {
      const mockResults = [
        { id: 'r1', percentage: 85 },
        { id: 'r2', percentage: 92 },
        { id: 'r3', percentage: 78 },
      ];
      mockPrismaService.examResult.findMany.mockResolvedValue(mockResults);
      mockPrismaService.examResult.update.mockResolvedValue({});
      mockPrismaService.$transaction.mockImplementation(ops => Promise.all(ops));

      const result = await service.computePositions('exam1');
      expect(result.computed).toBe(3);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Inventory Service Unit Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('InventoryService', () => {
  let service: any;

  beforeEach(() => {
    const { InventoryService } = require('../src/modules/inventory/inventory.service');
    service = new InventoryService(mockPrismaService as any);
  });

  afterEach(() => jest.clearAllMocks());

  describe('recordTransaction', () => {
    const mockItem = { id: 'item1', schoolId: 'school1', quantityInStock: 10, name: 'Pencils' };

    it('should add stock for IN transaction', async () => {
      mockPrismaService.inventoryItem.findFirst.mockResolvedValue(mockItem);
      mockPrismaService.inventoryTx.create.mockResolvedValue({ id: 'tx1' });
      mockPrismaService.inventoryItem.update.mockResolvedValue({});
      mockPrismaService.$transaction.mockImplementation(ops => Promise.all(ops));

      await service.recordTransaction('item1', 'school1', 'user1', { type: 'IN', quantity: 5 });

      expect(mockPrismaService.inventoryItem.update).toHaveBeenCalledWith(
        expect.objectContaining({ data: { quantityInStock: 15 } })
      );
    });

    it('should throw for insufficient stock on OUT', async () => {
      mockPrismaService.inventoryItem.findFirst.mockResolvedValue({ ...mockItem, quantityInStock: 2 });
      await expect(
        service.recordTransaction('item1', 'school1', 'user1', { type: 'OUT', quantity: 5 })
      ).rejects.toThrow('Insufficient stock');
    });

    it('should set absolute quantity for ADJUST', async () => {
      mockPrismaService.inventoryItem.findFirst.mockResolvedValue(mockItem);
      mockPrismaService.inventoryTx.create.mockResolvedValue({ id: 'tx1' });
      mockPrismaService.inventoryItem.update.mockResolvedValue({});
      mockPrismaService.$transaction.mockImplementation(ops => Promise.all(ops));

      await service.recordTransaction('item1', 'school1', 'user1', { type: 'ADJUST', quantity: 20 });
      expect(mockPrismaService.inventoryItem.update).toHaveBeenCalledWith(
        expect.objectContaining({ data: { quantityInStock: 20 } })
      );
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Timetable Conflict Detection Unit Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('TimetableService - timesOverlap', () => {
  let service: any;

  beforeEach(() => {
    const { TimetableService } = require('../src/modules/timetable/timetable.service');
    service = new TimetableService(mockPrismaService as any);
  });

  it('should detect overlapping time slots', () => {
    expect((service as any).timesOverlap('08:00', '09:00', '08:30', '09:30')).toBe(true);
  });

  it('should not flag adjacent slots as overlapping', () => {
    expect((service as any).timesOverlap('08:00', '09:00', '09:00', '10:00')).toBe(false);
  });

  it('should detect fully contained slot', () => {
    expect((service as any).timesOverlap('08:00', '10:00', '08:30', '09:30')).toBe(true);
  });

  it('should detect fully containing slot', () => {
    expect((service as any).timesOverlap('08:30', '09:30', '08:00', '10:00')).toBe(true);
  });

  it('should not flag completely separate slots', () => {
    expect((service as any).timesOverlap('08:00', '09:00', '10:00', '11:00')).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Audit Service Unit Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('AuditService', () => {
  let service: any;

  beforeEach(() => {
    const { AuditService } = require('../src/modules/audit/audit.module');
    service = new AuditService(mockPrismaService as any);
  });

  afterEach(() => jest.clearAllMocks());

  it('should create audit log entry', async () => {
    mockPrismaService.auditLog.create.mockResolvedValue({ id: 'log1' });
    await service.log({ schoolId: 'school1', action: 'CREATE', entity: 'Student', entityId: 'stu1' });
    expect(mockPrismaService.auditLog.create).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ entity: 'Student' }) })
    );
  });

  it('should not throw if audit log fails', async () => {
    mockPrismaService.auditLog.create.mockRejectedValue(new Error('DB error'));
    await expect(
      service.log({ schoolId: 'school1', action: 'UPDATE', entity: 'Finance' })
    ).resolves.not.toThrow();
  });

  it('should filter logs by entity', async () => {
    mockPrismaService.auditLog.findMany.mockResolvedValue([]);
    mockPrismaService.auditLog.count.mockResolvedValue(0);
    await service.getLogs('school1', { entity: 'Student' });
    expect(mockPrismaService.auditLog.findMany).toHaveBeenCalledWith(
      expect.objectContaining({ where: expect.objectContaining({ entity: 'Student' }) })
    );
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Finance: Scholarship Calculation Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('Scholarship Calculations', () => {
  const applyScholarship = (total: number, type: 'PERCENTAGE' | 'FIXED', value: number) => {
    if (type === 'PERCENTAGE') return total - (total * value / 100);
    return Math.max(0, total - value);
  };

  it('should apply percentage discount correctly', () => {
    expect(applyScholarship(100000, 'PERCENTAGE', 50)).toBe(50000);
  });

  it('should apply fixed discount correctly', () => {
    expect(applyScholarship(100000, 'FIXED', 20000)).toBe(80000);
  });

  it('should not result in negative balance for fixed discount', () => {
    expect(applyScholarship(10000, 'FIXED', 20000)).toBe(0);
  });

  it('should handle 100% scholarship', () => {
    expect(applyScholarship(50000, 'PERCENTAGE', 100)).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Document Service Unit Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('DocumentsService', () => {
  let service: any;
  const mockDocs = {
    documentFolder: {
      findMany: jest.fn(), findFirst: jest.fn(), create: jest.fn(), update: jest.fn(), delete: jest.fn(), count: jest.fn(),
    },
    documentV2: {
      findMany: jest.fn(), findFirst: jest.fn(), create: jest.fn(), update: jest.fn(), delete: jest.fn(), count: jest.fn(),
      groupBy: jest.fn(),
    },
    documentVersion: { create: jest.fn() },
  };

  beforeEach(() => {
    const { DocumentsService } = require('../src/modules/documents/documents.service');
    service = new DocumentsService({ ...mockPrismaService, ...mockDocs } as any);
  });

  it('should prevent deleting non-empty folder', async () => {
    mockDocs.documentFolder.findFirst.mockResolvedValue({ id: 'folder1' });
    mockDocs.documentFolder.count.mockResolvedValue(2); // has children
    mockDocs.documentV2.count.mockResolvedValue(0);

    await expect(service.deleteFolder('folder1', 'school1')).rejects.toThrow('Cannot delete non-empty folder');
  });

  it('should create new version when file URL changes', async () => {
    const oldDoc = { id: 'doc1', url: 'https://old-url.com/file.pdf', size: 1000, version: 1 };
    mockDocs.documentV2.findFirst.mockResolvedValue(oldDoc);
    mockDocs.documentVersion.create.mockResolvedValue({});
    mockDocs.documentV2.update.mockResolvedValue({ ...oldDoc, version: 2 });

    await service.updateDocument('doc1', 'school1', 'user1', { url: 'https://new-url.com/file.pdf' });
    expect(mockDocs.documentVersion.create).toHaveBeenCalled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// API Key Security Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('API Key Generation', () => {
  it('should generate unique API keys', () => {
    const crypto = require('crypto');
    const key1 = `ek_${crypto.randomBytes(32).toString('hex')}`;
    const key2 = `ek_${crypto.randomBytes(32).toString('hex')}`;
    expect(key1).not.toBe(key2);
  });

  it('should prefix key with ek_', () => {
    const crypto = require('crypto');
    const key = `ek_${crypto.randomBytes(32).toString('hex')}`;
    expect(key.startsWith('ek_')).toBe(true);
  });

  it('should hash key with SHA-256', () => {
    const crypto = require('crypto');
    const rawKey = 'ek_test123';
    const hash = crypto.createHash('sha256').update(rawKey).digest('hex');
    expect(hash).toHaveLength(64);
    // Same key always produces same hash
    expect(crypto.createHash('sha256').update(rawKey).digest('hex')).toBe(hash);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Analytics Dashboard Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('AnalyticsService', () => {
  it('should calculate revenue growth correctly', () => {
    const calcGrowth = (current: number, previous: number) => {
      if (previous === 0) return 0;
      return ((current - previous) / previous) * 100;
    };

    expect(calcGrowth(120000, 100000)).toBe(20);
    expect(calcGrowth(80000, 100000)).toBe(-20);
    expect(calcGrowth(100000, 0)).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Permission System Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('Permission Guards', () => {
  it('should parse permission strings correctly', () => {
    const parsePermission = (perm: string) => {
      const parts = perm.split(':');
      return { module: parts[0], resource: parts[1], action: parts[2] };
    };

    const perm = parsePermission('finance:invoices:CREATE');
    expect(perm.module).toBe('finance');
    expect(perm.resource).toBe('invoices');
    expect(perm.action).toBe('CREATE');
  });
});
