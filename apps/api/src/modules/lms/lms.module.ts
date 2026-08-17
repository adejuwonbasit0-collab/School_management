import { Module, Global } from '@nestjs/common';
import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Patch, Body, Param, Query, Req, UseGuards, HttpCode } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';
import { DatabaseModule } from '../../database/database.module';
import { NotificationsModule } from '../notifications/notifications.module';
import { NotificationsService } from '../notifications/notifications.service';

// ─── LMS Prisma helpers (uses existing schema relations) ─────────────────────
// Courses live as a CMS-style construct; we store them in the DB via existing
// models. We extend with lightweight in-module tables via raw queries or
// existing LibraryItem / Document patterns. For Phase 3 completeness we store
// courses as a JSON-rich record in the `customPage` table keyed by type.
// A production upgrade would add Course, CourseModule, Assignment, Quiz models.

@Injectable()
export class LmsService {
  constructor(
    private prisma: PrismaService,
    private notifications: NotificationsService,
  ) {}

  // ── Courses ──────────────────────────────────────────────────────────────

  async getCourses(schoolId: string, query: any = {}) {
    const { search, classRoomId, teacherId, page = 1, limit = 20 } = query;
    const where: any = { schoolId, type: 'COURSE' };
    if (search) where.title = { contains: search, mode: 'insensitive' };
    if (classRoomId) where.slug = { startsWith: `class-${classRoomId}` };

    const [data, total] = await Promise.all([
      this.prisma.customPage.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
      this.prisma.customPage.count({ where }),
    ]);
    return { data: data.map(c => ({ ...c, meta: c.content as any })), total, page: +page, pages: Math.ceil(total / limit) };
  }

  async getCourse(id: string, schoolId: string) {
    const course = await this.prisma.customPage.findFirst({
      where: { id, schoolId, type: 'COURSE' },
    });
    if (!course) throw new NotFoundException('Course not found');
    return { ...course, meta: course.content as any };
  }

  async createCourse(schoolId: string, userId: string, dto: {
    title: string;
    description?: string;
    classRoomId?: string;
    subjectId?: string;
    coverImage?: string;
    objectives?: string[];
    duration?: string;
  }) {
    const slug = `course-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    return this.prisma.customPage.create({
      data: {
        schoolId,
        slug,
        title: dto.title,
        type: 'COURSE',
        isPublished: false,
        content: {
          description: dto.description,
          classRoomId: dto.classRoomId,
          subjectId: dto.subjectId,
          coverImage: dto.coverImage,
          objectives: dto.objectives || [],
          duration: dto.duration,
          createdBy: userId,
          modules: [],
          enrolledStudents: [],
        },
      },
    });
  }

  async updateCourse(id: string, schoolId: string, dto: any) {
    const course = await this.prisma.customPage.findFirst({ where: { id, schoolId, type: 'COURSE' } });
    if (!course) throw new NotFoundException('Course not found');
    const existingContent = course.content as any;
    return this.prisma.customPage.update({
      where: { id },
      data: {
        title: dto.title || course.title,
        isPublished: dto.isPublished !== undefined ? dto.isPublished : course.isPublished,
        content: { ...existingContent, ...dto.meta },
      },
    });
  }

  async deleteCourse(id: string, schoolId: string) {
    const course = await this.prisma.customPage.findFirst({ where: { id, schoolId, type: 'COURSE' } });
    if (!course) throw new NotFoundException('Course not found');
    return this.prisma.customPage.delete({ where: { id } });
  }

  async publishCourse(id: string, schoolId: string) {
    return this.prisma.customPage.update({
      where: { id },
      data: { isPublished: true },
    });
  }

  // ── Course Modules / Materials ────────────────────────────────────────────

  async addMaterial(courseId: string, schoolId: string, dto: {
    title: string;
    type: 'VIDEO' | 'PDF' | 'NOTE' | 'LINK' | 'QUIZ' | 'ASSIGNMENT';
    url?: string;
    content?: string;
    duration?: number;
    order?: number;
  }) {
    const course = await this.prisma.customPage.findFirst({ where: { id: courseId, schoolId } });
    if (!course) throw new NotFoundException('Course not found');

    const content = course.content as any;
    const modules = content.modules || [];
    const newModule = {
      id: `mod-${Date.now()}`,
      ...dto,
      order: dto.order ?? modules.length,
      createdAt: new Date().toISOString(),
    };
    modules.push(newModule);

    await this.prisma.customPage.update({
      where: { id: courseId },
      data: { content: { ...content, modules } },
    });
    return newModule;
  }

  async removeMaterial(courseId: string, materialId: string, schoolId: string) {
    const course = await this.prisma.customPage.findFirst({ where: { id: courseId, schoolId } });
    if (!course) throw new NotFoundException('Course not found');
    const content = course.content as any;
    content.modules = (content.modules || []).filter((m: any) => m.id !== materialId);
    await this.prisma.customPage.update({ where: { id: courseId }, data: { content } });
    return { deleted: materialId };
  }

  // ── Enrollment ────────────────────────────────────────────────────────────

  async enrollStudent(courseId: string, studentId: string, schoolId: string) {
    const course = await this.prisma.customPage.findFirst({ where: { id: courseId, schoolId } });
    if (!course) throw new NotFoundException('Course not found');
    const content = course.content as any;
    const enrolled = content.enrolledStudents || [];
    if (!enrolled.includes(studentId)) enrolled.push(studentId);
    await this.prisma.customPage.update({ where: { id: courseId }, data: { content: { ...content, enrolledStudents: enrolled } } });

    // Notify student
    await this.notifications.sendNotification({
      userId: studentId,
      type: 'IN_APP',
      title: `Enrolled in ${course.title}`,
      body: `You have been enrolled in the course "${course.title}"`,
      data: { courseId },
    });
    return { enrolled: true, courseId, studentId };
  }

  async getEnrolledCourses(studentId: string, schoolId: string) {
    const courses = await this.prisma.customPage.findMany({
      where: { schoolId, type: 'COURSE', isPublished: true },
    });
    return courses.filter(c => {
      const content = c.content as any;
      return (content.enrolledStudents || []).includes(studentId);
    });
  }

  // ── Progress Tracking ─────────────────────────────────────────────────────

  async markProgress(courseId: string, studentId: string, materialId: string, completed: boolean) {
    // Store progress in document metadata
    const key = `progress-${courseId}-${studentId}`;
    const existing = await this.prisma.documentV2.findFirst({
      where: { schoolId: 'system', name: key },
    }).catch(() => null);

    const progress = (existing?.url ? JSON.parse(existing.url) : {}) as Record<string, boolean>;
    progress[materialId] = completed;

    if (existing) {
      await this.prisma.documentV2.update({
        where: { id: existing.id },
        data: { url: JSON.stringify(progress) },
      });
    } else {
      await this.prisma.documentV2.create({
        data: { schoolId: 'system', name: key, fileType: 'json', url: JSON.stringify(progress), uploadedBy: studentId },
      });
    }
    return { courseId, studentId, materialId, completed };
  }

  async getProgress(courseId: string, studentId: string) {
    const key = `progress-${courseId}-${studentId}`;
    const record = await this.prisma.documentV2.findFirst({
      where: { schoolId: 'system', name: key },
    }).catch(() => null);

    const progress = record?.url ? JSON.parse(record.url) : {};
    return { courseId, studentId, completedMaterials: progress };
  }

  // ── Assignments ───────────────────────────────────────────────────────────

  async submitAssignment(courseId: string, materialId: string, studentId: string, dto: {
    content?: string;
    fileUrl?: string;
  }) {
    const key = `assignment-${courseId}-${materialId}-${studentId}`;
    return this.prisma.documentV2.upsert({
      where: { id: key },
      create: {
        id: key,
        schoolId: 'system',
        name: key,
        fileType: 'assignment',
        url: JSON.stringify({ content: dto.content, fileUrl: dto.fileUrl, submittedAt: new Date() }),
        uploadedBy: studentId,
        studentId,
      },
      update: {
        url: JSON.stringify({ content: dto.content, fileUrl: dto.fileUrl, submittedAt: new Date() }),
      },
    });
  }

  async getAssignmentSubmissions(courseId: string, materialId: string) {
    return this.prisma.documentV2.findMany({
      where: { name: { startsWith: `assignment-${courseId}-${materialId}-` }, fileType: 'assignment' },
    });
  }

  async gradeAssignment(submissionId: string, grade: number, feedback: string, gradedBy: string) {
    const submission = await this.prisma.documentV2.findUnique({ where: { id: submissionId } });
    if (!submission) throw new NotFoundException('Submission not found');
    const data = JSON.parse(submission.url);
    data.grade = grade;
    data.feedback = feedback;
    data.gradedBy = gradedBy;
    data.gradedAt = new Date();
    await this.prisma.documentV2.update({ where: { id: submissionId }, data: { url: JSON.stringify(data) } });

    // Notify student
    await this.notifications.sendNotification({
      userId: submission.studentId || submission.uploadedBy,
      type: 'IN_APP',
      title: 'Assignment Graded',
      body: `Your assignment received grade: ${grade}/100. ${feedback}`,
    });
    return { graded: true, grade, feedback };
  }

  // ── Quizzes ───────────────────────────────────────────────────────────────

  async submitQuiz(courseId: string, quizId: string, studentId: string, answers: Record<string, any>) {
    // Quiz questions stored in course content; auto-grade by comparing to correct answers
    const course = await this.prisma.customPage.findFirst({ where: { id: courseId } });
    if (!course) throw new NotFoundException('Course not found');

    const content = course.content as any;
    const quiz = (content.modules || []).find((m: any) => m.id === quizId);
    if (!quiz) throw new NotFoundException('Quiz not found');

    const questions: any[] = quiz.questions || [];
    let correct = 0;
    const results = questions.map((q: any) => {
      const isCorrect = answers[q.id] === q.correctAnswer;
      if (isCorrect) correct++;
      return { questionId: q.id, submitted: answers[q.id], correct: q.correctAnswer, isCorrect };
    });

    const score = questions.length > 0 ? (correct / questions.length) * 100 : 0;

    // Store result
    const key = `quiz-${courseId}-${quizId}-${studentId}`;
    await this.prisma.documentV2.upsert({
      where: { id: key },
      create: { id: key, schoolId: 'system', name: key, fileType: 'quiz', url: JSON.stringify({ score, results, submittedAt: new Date() }), uploadedBy: studentId, studentId },
      update: { url: JSON.stringify({ score, results, submittedAt: new Date() }) },
    });

    return { score: score.toFixed(1), correct, total: questions.length, results };
  }

  // ── LMS Stats ─────────────────────────────────────────────────────────────

  async getLmsStats(schoolId: string) {
    const courses = await this.prisma.customPage.findMany({ where: { schoolId, type: 'COURSE' } });
    const totalCourses = courses.length;
    const publishedCourses = courses.filter(c => c.isPublished).length;
    const totalEnrollments = courses.reduce((acc, c) => {
      const content = c.content as any;
      return acc + (content.enrolledStudents?.length || 0);
    }, 0);
    return { totalCourses, publishedCourses, totalEnrollments };
  }
}

@Controller('lms')
@UseGuards(JwtAuthGuard, PermissionsGuard)
class LmsController {
  constructor(private readonly lms: LmsService) {}

  // Stats
  @Get('stats') @RequirePermissions('lms:courses:READ') stats(@Req() r: any) { return this.lms.getLmsStats(r.user.schoolId); }

  // Courses
  @Get('courses') @RequirePermissions('lms:courses:READ') getCourses(@Req() r: any, @Query() q: any) { return this.lms.getCourses(r.user.schoolId, q); }
  @Get('courses/:id') @RequirePermissions('lms:courses:READ') getCourse(@Param('id') id: string, @Req() r: any) { return this.lms.getCourse(id, r.user.schoolId); }
  @Post('courses') @RequirePermissions('lms:courses:CREATE') createCourse(@Req() r: any, @Body() b: any) { return this.lms.createCourse(r.user.schoolId, r.user.id, b); }
  @Put('courses/:id') @RequirePermissions('lms:courses:UPDATE') updateCourse(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.lms.updateCourse(id, r.user.schoolId, b); }
  @Delete('courses/:id') @RequirePermissions('lms:courses:DELETE') deleteCourse(@Param('id') id: string, @Req() r: any) { return this.lms.deleteCourse(id, r.user.schoolId); }
  @Patch('courses/:id/publish') @RequirePermissions('lms:courses:UPDATE') @HttpCode(200) publishCourse(@Param('id') id: string, @Req() r: any) { return this.lms.publishCourse(id, r.user.schoolId); }

  // Materials
  @Post('courses/:id/materials') @RequirePermissions('lms:courses:UPDATE') addMaterial(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.lms.addMaterial(id, r.user.schoolId, b); }
  @Delete('courses/:id/materials/:materialId') @RequirePermissions('lms:courses:UPDATE') removeMaterial(@Param('id') id: string, @Param('materialId') mid: string, @Req() r: any) { return this.lms.removeMaterial(id, mid, r.user.schoolId); }

  // Enrollment
  @Post('courses/:id/enroll') @HttpCode(200) enroll(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.lms.enrollStudent(id, b.studentId || r.user.id, r.user.schoolId); }
  @Get('my-courses') myCourses(@Req() r: any) { return this.lms.getEnrolledCourses(r.user.id, r.user.schoolId); }

  // Progress
  @Post('courses/:id/progress') markProgress(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.lms.markProgress(id, r.user.id, b.materialId, b.completed); }
  @Get('courses/:id/progress') getProgress(@Param('id') id: string, @Req() r: any) { return this.lms.getProgress(id, r.user.id); }

  // Assignments
  @Post('courses/:id/assignments/:materialId/submit') submitAssignment(@Param('id') cid: string, @Param('materialId') mid: string, @Req() r: any, @Body() b: any) { return this.lms.submitAssignment(cid, mid, r.user.id, b); }
  @Get('courses/:id/assignments/:materialId/submissions') @RequirePermissions('lms:courses:UPDATE') getSubmissions(@Param('id') cid: string, @Param('materialId') mid: string) { return this.lms.getAssignmentSubmissions(cid, mid); }
  @Put('submissions/:id/grade') @RequirePermissions('lms:courses:UPDATE') gradeAssignment(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.lms.gradeAssignment(id, b.grade, b.feedback, r.user.id); }

  // Quizzes
  @Post('courses/:id/quizzes/:quizId/submit') submitQuiz(@Param('id') cid: string, @Param('quizId') qid: string, @Req() r: any, @Body() b: any) { return this.lms.submitQuiz(cid, qid, r.user.id, b.answers); }
}

// Extend CustomPage type to support COURSE type
// Note: The existing CustomPage model's content field is JSON, we use `type` as a slug prefix

@Module({
  imports: [DatabaseModule, NotificationsModule],
  controllers: [LmsController],
  providers: [LmsService],
  exports: [LmsService],
})
export class LmsModule {}
