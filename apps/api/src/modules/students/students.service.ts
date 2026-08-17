import {
  Injectable,
  NotFoundException,
  ConflictException,
  BadRequestException,
} from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { EventEmitter2 } from '@nestjs/event-emitter';
import { CreateStudentDto, UpdateStudentDto, EnrollStudentDto, StudentQueryDto } from './dto';
import * as bcrypt from 'bcryptjs';
import { nanoid } from 'nanoid';

@Injectable()
export class StudentsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  // ─── List Students ───────────────────────────────────────────────────────────
  async findAll(schoolId: string, query: StudentQueryDto) {
    const {
      page = 1,
      limit = 20,
      search,
      classRoomId,
      academicYearId,
      sortBy = 'createdAt',
      sortOrder = 'desc',
    } = query;

    const skip = (page - 1) * limit;

    const where: any = {
      schoolId,
      ...(search && {
        OR: [
          { admissionNo: { contains: search, mode: 'insensitive' } },
          { user: { firstName: { contains: search, mode: 'insensitive' } } },
          { user: { lastName: { contains: search, mode: 'insensitive' } } },
          { user: { email: { contains: search, mode: 'insensitive' } } },
        ],
      }),
      ...(classRoomId && {
        enrollments: {
          some: {
            classRoomId,
            isCurrent: true,
            ...(academicYearId && { academicYearId }),
          },
        },
      }),
    };

    const [students, total] = await Promise.all([
      this.prisma.student.findMany({
        where,
        skip,
        take: limit,
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              email: true,
              phone: true,
              avatar: true,
              gender: true,
              dateOfBirth: true,
              status: true,
            },
          },
          enrollments: {
            where: { isCurrent: true },
            include: {
              classRoom: { select: { id: true, name: true, section: true } },
              academicYear: { select: { id: true, name: true } },
            },
          },
          parents: {
            include: {
              parent: {
                include: {
                  user: {
                    select: { firstName: true, lastName: true, phone: true, email: true },
                  },
                },
              },
            },
          },
        },
        orderBy: sortBy === 'name'
          ? [{ user: { firstName: sortOrder } }]
          : { [sortBy]: sortOrder },
      }),
      this.prisma.student.count({ where }),
    ]);

    return {
      data: students,
      meta: {
        total,
        page,
        limit,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  // ─── Find One ────────────────────────────────────────────────────────────────
  async findOne(schoolId: string, id: string) {
    const student = await this.prisma.student.findFirst({
      where: { id, schoolId },
      include: {
        user: true,
        enrollments: {
          include: {
            classRoom: true,
            academicYear: true,
          },
          orderBy: { createdAt: 'desc' },
        },
        parents: {
          include: {
            parent: {
              include: {
                user: {
                  select: {
                    id: true, firstName: true, lastName: true,
                    email: true, phone: true, avatar: true,
                  },
                },
              },
            },
          },
        },
        attendance: {
          take: 30,
          orderBy: { date: 'desc' },
          include: { classRoom: { select: { name: true } } },
        },
        feeInvoices: {
          include: {
            payments: { orderBy: { createdAt: 'desc' } },
          },
          orderBy: { createdAt: 'desc' },
        },
        documents: { orderBy: { createdAt: 'desc' } },
        admissionRecord: true,
        hostelResident: { include: { room: { include: { hostel: true } } } },
        transportStudent: { include: { route: true } },
        libraryBorrows: {
          where: { returnedAt: null },
          include: { item: { select: { title: true, author: true } } },
        },
      },
    });

    if (!student) throw new NotFoundException('Student not found');
    return student;
  }

  // ─── Create Student ──────────────────────────────────────────────────────────
  async create(schoolId: string, dto: CreateStudentDto, createdBy: string) {
    const school = await this.prisma.school.findUnique({
      where: { id: schoolId },
      select: { id: true, name: true },
    });
    if (!school) throw new NotFoundException('School not found');

    // Generate admission number
    const admissionNo = await this.generateAdmissionNo(schoolId);

    // Check for duplicate email
    const existingUser = await this.prisma.user.findUnique({
      where: { email: dto.email.toLowerCase() },
    });
    if (existingUser) throw new ConflictException('Email already registered');

    const passwordHash = await bcrypt.hash(dto.password || `Student${admissionNo}!`, 12);

    const result = await this.prisma.$transaction(async (tx) => {
      // Create user account
      const user = await tx.user.create({
        data: {
          email: dto.email.toLowerCase(),
          passwordHash,
          firstName: dto.firstName,
          lastName: dto.lastName,
          middleName: dto.middleName,
          phone: dto.phone,
          gender: dto.gender,
          dateOfBirth: dto.dateOfBirth ? new Date(dto.dateOfBirth) : undefined,
          address: dto.address,
          city: dto.city,
          state: dto.state,
          country: dto.country,
          avatar: dto.avatar,
          status: 'ACTIVE',
          schoolId,
        },
      });

      // Assign student role
      const studentRole = await tx.role.findFirst({
        where: { schoolId, slug: 'student' },
      });
      if (studentRole) {
        await tx.userRole.create({
          data: { userId: user.id, roleId: studentRole.id, assignedBy: createdBy },
        });
      }

      // Create student profile
      const student = await tx.student.create({
        data: {
          userId: user.id,
          schoolId,
          admissionNo,
          admissionDate: dto.admissionDate ? new Date(dto.admissionDate) : new Date(),
          bloodGroup: dto.bloodGroup,
          nationality: dto.nationality,
          religion: dto.religion,
          motherTongue: dto.motherTongue,
          previousSchool: dto.previousSchool,
          medicalConditions: dto.medicalConditions,
          allergies: dto.allergies,
        },
      });

      // Enroll in class if provided
      if (dto.classRoomId && dto.academicYearId) {
        await tx.studentEnrollment.create({
          data: {
            studentId: student.id,
            classRoomId: dto.classRoomId,
            academicYearId: dto.academicYearId,
            rollNumber: dto.rollNumber,
            isCurrent: true,
          },
        });
      }

      // Link parents if provided
      if (dto.parents && dto.parents.length > 0) {
        for (const parentData of dto.parents) {
          await this.linkOrCreateParent(tx, student.id, parentData, schoolId);
        }
      }

      return student;
    });

    this.eventEmitter.emit('student.created', {
      studentId: result.id,
      schoolId,
      admissionNo,
      createdBy,
    });

    return this.findOne(schoolId, result.id);
  }

  // ─── Update Student ──────────────────────────────────────────────────────────
  async update(schoolId: string, id: string, dto: UpdateStudentDto) {
    const student = await this.prisma.student.findFirst({
      where: { id, schoolId },
    });
    if (!student) throw new NotFoundException('Student not found');

    await this.prisma.$transaction([
      this.prisma.user.update({
        where: { id: student.userId },
        data: {
          firstName: dto.firstName,
          lastName: dto.lastName,
          middleName: dto.middleName,
          phone: dto.phone,
          gender: dto.gender,
          dateOfBirth: dto.dateOfBirth ? new Date(dto.dateOfBirth) : undefined,
          address: dto.address,
          city: dto.city,
          state: dto.state,
          country: dto.country,
          avatar: dto.avatar,
        },
      }),
      this.prisma.student.update({
        where: { id },
        data: {
          bloodGroup: dto.bloodGroup,
          nationality: dto.nationality,
          religion: dto.religion,
          motherTongue: dto.motherTongue,
          previousSchool: dto.previousSchool,
          medicalConditions: dto.medicalConditions,
          allergies: dto.allergies,
          disabilities: dto.disabilities,
        },
      }),
    ]);

    return this.findOne(schoolId, id);
  }

  // ─── Enroll / Transfer Student ───────────────────────────────────────────────
  async enroll(schoolId: string, studentId: string, dto: EnrollStudentDto) {
    const student = await this.prisma.student.findFirst({
      where: { id: studentId, schoolId },
    });
    if (!student) throw new NotFoundException('Student not found');

    const classRoom = await this.prisma.classRoom.findFirst({
      where: { id: dto.classRoomId, schoolId },
    });
    if (!classRoom) throw new NotFoundException('Class not found');

    // Check capacity
    const enrolledCount = await this.prisma.studentEnrollment.count({
      where: { classRoomId: dto.classRoomId, academicYearId: dto.academicYearId, isCurrent: true },
    });
    if (enrolledCount >= classRoom.capacity) {
      throw new BadRequestException('Class is at full capacity');
    }

    // Mark previous enrollments as not current
    await this.prisma.studentEnrollment.updateMany({
      where: { studentId, isCurrent: true },
      data: { isCurrent: false },
    });

    const enrollment = await this.prisma.studentEnrollment.create({
      data: {
        studentId,
        classRoomId: dto.classRoomId,
        academicYearId: dto.academicYearId,
        rollNumber: dto.rollNumber,
        isCurrent: true,
      },
    });

    return enrollment;
  }

  // ─── Promote Students ────────────────────────────────────────────────────────
  async promoteStudents(
    schoolId: string,
    fromClassId: string,
    toClassId: string,
    academicYearId: string,
    studentIds: string[],
  ) {
    const promotions = await this.prisma.$transaction(
      studentIds.map((studentId) =>
        this.prisma.studentEnrollment.create({
          data: {
            studentId,
            classRoomId: toClassId,
            academicYearId,
            isCurrent: true,
            promotedFrom: fromClassId,
          },
        }),
      ),
    );

    // Mark old enrollments as not current
    await this.prisma.studentEnrollment.updateMany({
      where: {
        studentId: { in: studentIds },
        classRoomId: fromClassId,
        isCurrent: true,
      },
      data: { isCurrent: false, promotedTo: toClassId },
    });

    this.eventEmitter.emit('students.promoted', {
      schoolId,
      fromClassId,
      toClassId,
      studentIds,
      academicYearId,
    });

    return { promoted: promotions.length };
  }

  // ─── Student Statistics ──────────────────────────────────────────────────────
  async getStats(schoolId: string) {
    const [
      totalStudents,
      activeEnrollments,
      genderStats,
      classDistribution,
    ] = await Promise.all([
      this.prisma.student.count({ where: { schoolId } }),
      this.prisma.studentEnrollment.count({
        where: { student: { schoolId }, isCurrent: true },
      }),
      this.prisma.user.groupBy({
        by: ['gender'],
        where: { student: { schoolId } },
        _count: true,
      }),
      this.prisma.studentEnrollment.groupBy({
        by: ['classRoomId'],
        where: { student: { schoolId }, isCurrent: true },
        _count: true,
        orderBy: { _count: { classRoomId: 'desc' } },
        take: 10,
      }),
    ]);

    return {
      totalStudents,
      activeEnrollments,
      genderStats,
      classDistribution,
    };
  }

  // ─── Delete Student ──────────────────────────────────────────────────────────
  async remove(schoolId: string, id: string) {
    const student = await this.prisma.student.findFirst({
      where: { id, schoolId },
    });
    if (!student) throw new NotFoundException('Student not found');

    // Soft delete by deactivating user
    await this.prisma.user.update({
      where: { id: student.userId },
      data: { status: 'ARCHIVED' },
    });

    return { message: 'Student archived successfully' };
  }

  // ─── Attendance Summary ──────────────────────────────────────────────────────
  async getAttendanceSummary(schoolId: string, studentId: string, termId: string) {
    const student = await this.prisma.student.findFirst({
      where: { id: studentId, schoolId },
    });
    if (!student) throw new NotFoundException('Student not found');

    const attendance = await this.prisma.attendance.groupBy({
      by: ['status'],
      where: { studentId, termId },
      _count: true,
    });

    const total = attendance.reduce((sum, a) => sum + a._count, 0);
    const present = attendance.find((a) => a.status === 'PRESENT')?._count || 0;
    const late = attendance.find((a) => a.status === 'LATE')?._count || 0;

    return {
      total,
      present,
      absent: attendance.find((a) => a.status === 'ABSENT')?._count || 0,
      late,
      excused: attendance.find((a) => a.status === 'EXCUSED')?._count || 0,
      percentage: total > 0 ? Math.round(((present + late) / total) * 100) : 0,
      breakdown: attendance,
    };
  }

  // ─── Private Helpers ─────────────────────────────────────────────────────────
  private async generateAdmissionNo(schoolId: string): Promise<string> {
    const year = new Date().getFullYear().toString().slice(-2);
    const count = await this.prisma.student.count({ where: { schoolId } });
    return `STU${year}${String(count + 1).padStart(4, '0')}`;
  }

  private async linkOrCreateParent(
    tx: any,
    studentId: string,
    parentData: any,
    schoolId: string,
  ) {
    let parent = await tx.parent.findFirst({
      where: { user: { email: parentData.email?.toLowerCase() } },
    });

    if (!parent) {
      const passwordHash = await bcrypt.hash(`Parent${nanoid(8)}!`, 12);
      const parentUser = await tx.user.create({
        data: {
          email: parentData.email?.toLowerCase(),
          passwordHash,
          firstName: parentData.firstName,
          lastName: parentData.lastName,
          phone: parentData.phone,
          status: 'ACTIVE',
          schoolId,
        },
      });

      const parentRole = await tx.role.findFirst({
        where: { schoolId, slug: 'parent' },
      });
      if (parentRole) {
        await tx.userRole.create({
          data: { userId: parentUser.id, roleId: parentRole.id },
        });
      }

      parent = await tx.parent.create({
        data: {
          userId: parentUser.id,
          occupation: parentData.occupation,
          workplace: parentData.workplace,
        },
      });
    }

    await tx.studentParent.create({
      data: {
        studentId,
        parentId: parent.id,
        relationship: parentData.relationship || 'PARENT',
        isPrimary: parentData.isPrimary || false,
      },
    });
  }
}
