import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { NotificationsService } from '../notifications/notifications.service';
import * as PDFDocument from 'pdfkit';

@Injectable()
export class ResultsService {
  constructor(
    private prisma: PrismaService,
    private notifications: NotificationsService,
  ) {}

  // ─── Grade Scale Management ──────────────────────────────────────────────

  async createGradeScale(schoolId: string, dto: {
    name: string;
    entries: { grade: string; minScore: number; maxScore: number; gradePoint: number; remark?: string }[];
  }) {
    return this.prisma.gradeScale.create({
      data: {
        schoolId,
        name: dto.name,
        grades: {
          create: dto.entries,
        },
      },
      include: { grades: true },
    });
  }

  async getGradeScales(schoolId: string) {
    return this.prisma.gradeScale.findMany({
      where: { schoolId },
      include: { grades: { orderBy: { minScore: 'desc' } } },
    });
  }

  async updateGradeScale(id: string, schoolId: string, dto: {
    name?: string;
    entries?: { grade: string; minScore: number; maxScore: number; gradePoint: number; remark?: string }[];
  }) {
    const existing = await this.prisma.gradeScale.findFirst({ where: { id, schoolId } });
    if (!existing) throw new NotFoundException('Grade scale not found');

    if (dto.entries) {
      await this.prisma.gradeScaleEntry.deleteMany({ where: { gradeScaleId: id } });
    }

    return this.prisma.gradeScale.update({
      where: { id },
      data: {
        name: dto.name,
        grades: dto.entries ? { create: dto.entries } : undefined,
      },
      include: { grades: true },
    });
  }

  async deleteGradeScale(id: string, schoolId: string) {
    const existing = await this.prisma.gradeScale.findFirst({ where: { id, schoolId } });
    if (!existing) throw new NotFoundException('Grade scale not found');
    return this.prisma.gradeScale.delete({ where: { id } });
  }

  // ─── Result Config ───────────────────────────────────────────────────────

  async getResultConfig(schoolId: string) {
    return this.prisma.resultConfig.findUnique({ where: { schoolId } });
  }

  async upsertResultConfig(schoolId: string, dto: {
    gradeScaleId?: string;
    caWeight?: number;
    examWeight?: number;
    passMark?: number;
    showPosition?: boolean;
    showGrade?: boolean;
    principalRemark?: string;
  }) {
    return this.prisma.resultConfig.upsert({
      where: { schoolId },
      create: { schoolId, ...dto },
      update: dto,
    });
  }

  // ─── Score Entry ─────────────────────────────────────────────────────────

  async upsertExamResult(examinationId: string, studentId: string, scores: Record<string, {
    caScore?: number; examScore?: number; maxScore?: number;
  }>, dto: { remarks?: string }) {
    const exam = await this.prisma.examination.findUnique({ where: { id: examinationId } });
    if (!exam) throw new NotFoundException('Examination not found');

    const config = await this.prisma.resultConfig.findUnique({ where: { schoolId: exam.schoolId } });
    const caWeight = config ? Number(config.caWeight) / 100 : 0.4;
    const examWeight = config ? Number(config.examWeight) / 100 : 0.6;

    // Calculate totals
    let totalScore = 0;
    let subjectCount = 0;
    const enrichedScores: Record<string, any> = {};

    for (const [subjectId, s] of Object.entries(scores)) {
      const ca = s.caScore || 0;
      const exam_score = s.examScore || 0;
      const max = s.maxScore || 100;
      const total = (ca * caWeight) + (exam_score * examWeight);
      const pct = (total / max) * 100;
      const grade = config?.gradeScaleId ? await this.resolveGrade(config.gradeScaleId, pct) : this.defaultGrade(pct);

      enrichedScores[subjectId] = {
        caScore: ca,
        examScore: exam_score,
        maxScore: max,
        totalScore: Math.round(total * 100) / 100,
        percentage: Math.round(pct * 100) / 100,
        grade: grade.letter,
        gradePoint: grade.point,
        remark: grade.remark,
      };

      totalScore += total;
      subjectCount++;
    }

    const avgPercentage = subjectCount > 0 ? totalScore / subjectCount : 0;
    const overallGrade = config?.gradeScaleId
      ? await this.resolveGrade(config.gradeScaleId, avgPercentage)
      : this.defaultGrade(avgPercentage);

    return this.prisma.examResult.upsert({
      where: { examinationId_studentId: { examinationId, studentId } },
      create: {
        examinationId,
        studentId,
        scores: enrichedScores,
        totalScore: totalScore,
        percentage: avgPercentage,
        grade: overallGrade.letter,
        remarks: dto.remarks,
      },
      update: {
        scores: enrichedScores,
        totalScore: totalScore,
        percentage: avgPercentage,
        grade: overallGrade.letter,
        remarks: dto.remarks,
      },
    });
  }

  async getExamResults(examinationId: string) {
    return this.prisma.examResult.findMany({
      where: { examinationId },
      include: {
        student: {
          include: { user: { select: { firstName: true, lastName: true } } },
        },
      },
      orderBy: { percentage: 'desc' },
    });
  }

  async getStudentResults(studentId: string, termId?: string) {
    const where: any = { studentId };
    if (termId) {
      where.examination = { termId };
    }
    return this.prisma.examResult.findMany({
      where,
      include: {
        examination: { include: { term: true, academicYear: true } },
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  // ─── Compute Positions ───────────────────────────────────────────────────

  async computePositions(examinationId: string) {
    const results = await this.prisma.examResult.findMany({
      where: { examinationId },
      orderBy: { percentage: 'desc' },
    });

    const updates = results.map((r, i) =>
      this.prisma.examResult.update({
        where: { id: r.id },
        data: { position: i + 1 },
      })
    );

    await this.prisma.$transaction(updates);
    return { computed: results.length };
  }

  // ─── Publish Results ─────────────────────────────────────────────────────

  async publishResults(examinationId: string, userId: string) {
    const exam = await this.prisma.examination.findUnique({
      where: { id: examinationId },
      include: { results: { include: { student: { include: { parents: { include: { parent: { include: { user: true } } } } } } } } },
    });
    if (!exam) throw new NotFoundException('Examination not found');

    await this.prisma.examination.update({
      where: { id: examinationId },
      data: { status: 'RESULTS_PUBLISHED' },
    });

    await this.prisma.examResult.updateMany({
      where: { examinationId },
      data: { publishedAt: new Date() },
    });

    // Notify parents
    for (const result of exam.results) {
      for (const sp of result.student.parents) {
        await this.notifications.sendNotification({
          userId: sp.parent.userId,
          type: 'IN_APP',
          title: `Results Published: ${exam.name}`,
          body: `Results for ${result.student.user?.firstName} have been published. Grade: ${result.grade}`,
          data: { examinationId, studentId: result.studentId },
        });
      }
    }

    return { published: exam.results.length };
  }

  // ─── Broadsheet ──────────────────────────────────────────────────────────

  async getBroadsheet(examinationId: string, classRoomId: string) {
    const exam = await this.prisma.examination.findUnique({
      where: { id: examinationId },
      include: { term: true, academicYear: true },
    });
    if (!exam) throw new NotFoundException('Examination not found');

    // Get subjects for class
    const classSubjects = await this.prisma.classSubject.findMany({
      where: { classRoomId },
      include: { subject: true },
    });

    // Get enrollments for class in this exam's academic year
    const enrollments = await this.prisma.studentEnrollment.findMany({
      where: { classRoomId, academicYearId: exam.academicYearId, isCurrent: true },
      include: {
        student: {
          include: {
            user: { select: { firstName: true, lastName: true } },
            examResults: { where: { examinationId } },
          },
        },
      },
    });

    const subjects = classSubjects.map(cs => ({ id: cs.subjectId, name: cs.subject.name, code: cs.subject.code }));

    const rows = enrollments.map(e => {
      const result = e.student.examResults[0];
      const scores = (result?.scores as Record<string, any>) || {};
      const subjectScores = subjects.map(s => scores[s.id] || { totalScore: '-', grade: '-' });

      return {
        studentId: e.student.id,
        admissionNo: e.student.admissionNo,
        name: `${e.student.user?.firstName} ${e.student.user?.lastName}`,
        rollNumber: e.rollNumber,
        subjects: subjectScores,
        totalScore: result?.totalScore || 0,
        percentage: result?.percentage || 0,
        grade: result?.grade || '-',
        position: result?.position || '-',
      };
    });

    rows.sort((a, b) => Number(b.percentage) - Number(a.percentage));

    return {
      examination: { id: exam.id, name: exam.name, term: exam.term?.name, year: exam.academicYear.name },
      subjects,
      rows,
    };
  }

  // ─── PDF Report Card ─────────────────────────────────────────────────────

  async generateReportCard(examinationId: string, studentId: string): Promise<Buffer> {
    const result = await this.prisma.examResult.findUnique({
      where: { examinationId_studentId: { examinationId, studentId } },
      include: {
        examination: { include: { term: true, academicYear: true } },
        student: {
          include: {
            user: true,
            school: true,
            enrollments: {
              where: { isCurrent: true },
              include: { classRoom: true },
            },
          },
        },
      },
    });

    if (!result) throw new NotFoundException('Result not found');

    const subjects = await this.prisma.classSubject.findMany({
      where: { classRoomId: result.student.enrollments[0]?.classRoomId },
      include: { subject: true },
    });

    const school = result.student.school;
    const student = result.student;
    const user = student.user;
    const scores = (result.scores as Record<string, any>) || {};

    return new Promise((resolve, reject) => {
      const doc = new PDFDocument({ size: 'A4', margin: 40 });
      const buffers: Buffer[] = [];
      doc.on('data', b => buffers.push(b));
      doc.on('end', () => resolve(Buffer.concat(buffers)));
      doc.on('error', reject);

      const primary = '#1a56db';
      const W = doc.page.width - 80;

      // Header
      doc.rect(40, 40, W, 90).fill(primary);
      doc.fillColor('white').fontSize(22).font('Helvetica-Bold')
        .text(school.name, 55, 55, { width: W - 20 });
      doc.fontSize(10).font('Helvetica')
        .text(`${school.address || ''} | ${school.phone || ''} | ${school.email || ''}`, 55, 82);
      doc.fontSize(14).font('Helvetica-Bold')
        .text('STUDENT REPORT CARD', 55, 104);

      // Term info box
      doc.fillColor('#333').fontSize(10).font('Helvetica');
      doc.rect(40, 145, W, 60).stroke('#ddd');
      doc.text(`Academic Year: ${result.examination.academicYear.name}`, 55, 155);
      doc.text(`Term: ${result.examination.term?.name || 'N/A'}`, 55, 170);
      doc.text(`Examination: ${result.examination.name}`, 250, 155);
      doc.text(`Date Generated: ${new Date().toLocaleDateString()}`, 250, 170);

      // Student info
      doc.rect(40, 215, W, 75).stroke('#ddd');
      doc.font('Helvetica-Bold').text('STUDENT INFORMATION', 55, 225);
      doc.font('Helvetica')
        .text(`Name: ${user.firstName} ${user.lastName}`, 55, 242)
        .text(`Admission No: ${student.admissionNo}`, 55, 257)
        .text(`Class: ${result.student.enrollments[0]?.classRoom?.name || 'N/A'}`, 300, 242)
        .text(`Position: ${result.position || 'N/A'}`, 300, 257);

      // Scores table
      let y = 305;
      doc.font('Helvetica-Bold').fontSize(9);
      doc.rect(40, y, W, 20).fill('#f0f4ff');
      doc.fillColor('#333')
        .text('SUBJECT', 50, y + 6)
        .text('CA SCORE', 210, y + 6)
        .text('EXAM SCORE', 280, y + 6)
        .text('TOTAL', 370, y + 6)
        .text('GRADE', 430, y + 6)
        .text('REMARK', 470, y + 6);

      y += 20;
      doc.font('Helvetica').fontSize(9);

      for (const cs of subjects) {
        const s = scores[cs.subjectId];
        if (!s) continue;
        if (y > 720) {
          doc.addPage();
          y = 40;
        }
        const bg = y % 40 === 0 ? '#fafafa' : 'white';
        doc.rect(40, y, W, 18).fill(bg).stroke('#eee');
        doc.fillColor('#222')
          .text(cs.subject.name, 50, y + 5)
          .text(String(s.caScore ?? '-'), 210, y + 5)
          .text(String(s.examScore ?? '-'), 280, y + 5)
          .text(String(s.totalScore ?? '-'), 370, y + 5)
          .text(String(s.grade ?? '-'), 430, y + 5)
          .text(String(s.remark ?? '-'), 470, y + 5);
        y += 18;
      }

      // Summary
      y += 15;
      doc.rect(40, y, W, 55).stroke('#ddd');
      doc.font('Helvetica-Bold').fontSize(10)
        .text('SUMMARY', 55, y + 8);
      doc.font('Helvetica').fontSize(10)
        .text(`Total Score: ${Number(result.totalScore).toFixed(1)}`, 55, y + 25)
        .text(`Percentage: ${Number(result.percentage).toFixed(1)}%`, 200, y + 25)
        .text(`Overall Grade: ${result.grade || 'N/A'}`, 370, y + 25);

      // Principal remark
      y += 70;
      doc.font('Helvetica-Bold').text("Principal's Remark:", 55, y);
      doc.font('Helvetica').text(result.remarks || 'Well done. Keep it up!', 55, y + 15, { width: W - 30 });

      // Signature line
      y += 60;
      doc.moveTo(55, y).lineTo(200, y).stroke();
      doc.text("Principal's Signature", 55, y + 5);
      doc.moveTo(300, y).lineTo(445, y).stroke();
      doc.text("Class Teacher's Signature", 300, y + 5);

      doc.end();
    });
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  private async resolveGrade(gradeScaleId: string, pct: number) {
    const entries = await this.prisma.gradeScaleEntry.findMany({
      where: { gradeScaleId },
      orderBy: { minScore: 'desc' },
    });
    for (const e of entries) {
      if (pct >= Number(e.minScore) && pct <= Number(e.maxScore)) {
        return { letter: e.grade, point: Number(e.gradePoint), remark: e.remark || '' };
      }
    }
    return { letter: 'F', point: 0, remark: 'Fail' };
  }

  private defaultGrade(pct: number) {
    if (pct >= 70) return { letter: 'A', point: 4.0, remark: 'Excellent' };
    if (pct >= 60) return { letter: 'B', point: 3.0, remark: 'Good' };
    if (pct >= 50) return { letter: 'C', point: 2.0, remark: 'Average' };
    if (pct >= 45) return { letter: 'D', point: 1.0, remark: 'Pass' };
    return { letter: 'F', point: 0, remark: 'Fail' };
  }
}
