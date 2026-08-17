import { Module } from '@nestjs/common';
import { Injectable, Logger } from '@nestjs/common';
import { Controller, Get, Post, Body, Param, Query, UseGuards } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId, CurrentUser } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';
import OpenAI from 'openai';

@Injectable()
export class AiService {
  private readonly logger = new Logger(AiService.name);
  private openai: OpenAI;

  constructor(
    private readonly prisma: PrismaService,
    private readonly config: ConfigService,
  ) {
    this.openai = new OpenAI({
      apiKey: this.config.get('ai.openaiApiKey'),
    });
  }

  private async getModuleConfig(schoolId: string, module: string) {
    return this.prisma.aiModuleConfig.findUnique({
      where: { schoolId_module: { schoolId, module } },
    });
  }

  private async isModuleEnabled(schoolId: string, module: string): Promise<boolean> {
    const cfg = await this.getModuleConfig(schoolId, module);
    return cfg?.isEnabled ?? false;
  }

  async getModuleConfigs(schoolId: string) {
    const defaults = [
      'tutor', 'question-generator', 'exam-generator', 'lesson-planner',
      'result-analyzer', 'performance-predictor', 'attendance-insights',
      'admission-screening', 'report-writer', 'chat-assistant',
    ];

    const existing = await this.prisma.aiModuleConfig.findMany({ where: { schoolId } });
    const existingMap = new Map<string, any>(existing.map((e: any) => [e.module, e]));

    return defaults.map((module) => ({
      module,
      isEnabled: existingMap.get(module)?.isEnabled ?? false,
      config: existingMap.get(module)?.config ?? {},
    }));
  }

  async toggleModule(schoolId: string, module: string, isEnabled: boolean, config?: any) {
    return this.prisma.aiModuleConfig.upsert({
      where: { schoolId_module: { schoolId, module } },
      create: { schoolId, module, isEnabled, config: config ?? {} },
      update: { isEnabled, config: config ?? {} },
    });
  }

  // ─── AI Tutor ────────────────────────────────────────────────────────────────
  async askTutor(schoolId: string, data: { question: string; subject?: string; level?: string }) {
    const enabled = await this.isModuleEnabled(schoolId, 'tutor');
    if (!enabled) return { error: 'AI Tutor is not enabled for this school' };

    try {
      const response = await this.openai.chat.completions.create({
        model: 'gpt-4o-mini',
        max_tokens: 1000,
        messages: [
          {
            role: 'system',
            content: `You are an expert educational tutor${data.subject ? ` specializing in ${data.subject}` : ''}${data.level ? ` for ${data.level} level students` : ''}. Provide clear, accurate, and educational responses. Use examples and analogies where helpful.`,
          },
          { role: 'user', content: data.question },
        ],
      });
      return { answer: response.choices[0].message.content };
    } catch (err) {
      this.logger.error(`AI Tutor error: ${err.message}`);
      throw err;
    }
  }

  // ─── Question Generator ──────────────────────────────────────────────────────
  async generateQuestions(schoolId: string, data: {
    subject: string;
    topic: string;
    level: string;
    count: number;
    type: 'multiple_choice' | 'true_false' | 'short_answer' | 'essay';
    difficulty: 'easy' | 'medium' | 'hard';
  }) {
    const enabled = await this.isModuleEnabled(schoolId, 'question-generator');
    if (!enabled) return { error: 'AI Question Generator is not enabled' };

    const typeInstructions = {
      multiple_choice: 'Generate multiple choice questions with 4 options (A, B, C, D) and indicate the correct answer.',
      true_false: 'Generate true/false questions with the correct answer.',
      short_answer: 'Generate short answer questions with model answers.',
      essay: 'Generate essay questions with marking guidelines.',
    };

    const prompt = `Generate ${data.count} ${data.difficulty} ${data.type.replace('_', ' ')} questions on the topic "${data.topic}" for ${data.subject} at ${data.level} level.

${typeInstructions[data.type]}

Return ONLY valid JSON array with this structure:
[
  {
    "question": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],  // for MCQ only
    "answer": "...",
    "explanation": "...",
    "marks": 2
  }
]`;

    try {
      const response = await this.openai.chat.completions.create({
        model: 'gpt-4o-mini',
        max_tokens: 2000,
        messages: [
          { role: 'system', content: 'You are an expert educator who creates high-quality exam questions. Always return valid JSON only.' },
          { role: 'user', content: prompt },
        ],
      });

      const content = response.choices[0].message.content?.replace(/```json\n?|\n?```/g, '') || '[]';
      const questions = JSON.parse(content);
      return { questions, count: questions.length, subject: data.subject, topic: data.topic };
    } catch (err) {
      this.logger.error(`Question generator error: ${err.message}`);
      throw err;
    }
  }

  // ─── Lesson Planner ──────────────────────────────────────────────────────────
  async generateLessonPlan(schoolId: string, data: {
    subject: string;
    topic: string;
    level: string;
    duration: number;
    objectives?: string[];
  }) {
    const enabled = await this.isModuleEnabled(schoolId, 'lesson-planner');
    if (!enabled) return { error: 'AI Lesson Planner is not enabled' };

    const prompt = `Create a detailed lesson plan for:
Subject: ${data.subject}
Topic: ${data.topic}
Level: ${data.level}
Duration: ${data.duration} minutes
${data.objectives ? `Objectives: ${data.objectives.join(', ')}` : ''}

Return ONLY valid JSON with this structure:
{
  "title": "...",
  "subject": "...",
  "level": "...",
  "duration": ${data.duration},
  "objectives": ["..."],
  "materials": ["..."],
  "introduction": { "duration": 5, "activities": ["..."] },
  "mainLesson": { "duration": ${Math.floor(data.duration * 0.6)}, "activities": ["..."], "teachingPoints": ["..."] },
  "activities": { "duration": ${Math.floor(data.duration * 0.2)}, "tasks": ["..."] },
  "assessment": { "duration": ${Math.floor(data.duration * 0.1)}, "methods": ["..."] },
  "conclusion": { "duration": 5, "summary": "..." },
  "homework": "...",
  "notes": "..."
}`;

    try {
      const response = await this.openai.chat.completions.create({
        model: 'gpt-4o-mini',
        max_tokens: 2000,
        messages: [
          { role: 'system', content: 'You are an experienced teacher creating structured lesson plans. Return only valid JSON.' },
          { role: 'user', content: prompt },
        ],
      });

      const content = response.choices[0].message.content?.replace(/```json\n?|\n?```/g, '') || '{}';
      return JSON.parse(content);
    } catch (err) {
      this.logger.error(`Lesson planner error: ${err.message}`);
      throw err;
    }
  }

  // ─── Result Analyzer ─────────────────────────────────────────────────────────
  async analyzeResults(schoolId: string, examinationId: string) {
    const enabled = await this.isModuleEnabled(schoolId, 'result-analyzer');
    if (!enabled) return { error: 'AI Result Analyzer is not enabled' };

    const results = await this.prisma.examResult.findMany({
      where: { examinationId },
      include: {
        student: { include: { user: { select: { firstName: true, lastName: true } } } },
        examination: { select: { name: true, type: true } },
      },
    });

    if (results.length === 0) return { error: 'No results found for this examination' };

    const scores = results.map((r) => Number(r.percentage || 0));
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    const max = Math.max(...scores);
    const min = Math.min(...scores);
    const passed = scores.filter((s) => s >= 50).length;

    const statsText = `
Examination: ${results[0].examination?.name}
Total students: ${results.length}
Average score: ${avg.toFixed(1)}%
Highest score: ${max}%
Lowest score: ${min}%
Pass rate: ${((passed / results.length) * 100).toFixed(1)}%
Score distribution: ${JSON.stringify(
      [0, 20, 40, 60, 80].map((threshold) => ({
        range: `${threshold}-${threshold + 20}%`,
        count: scores.filter((s) => s >= threshold && s < threshold + 20).length,
      })),
    )}`;

    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 800,
      messages: [
        { role: 'system', content: 'You are an educational data analyst. Provide concise, actionable insights from exam results.' },
        { role: 'user', content: `Analyze these examination results and provide insights:\n${statsText}\n\nProvide: 1) Key findings 2) Areas of concern 3) Recommendations for improvement` },
      ],
    });

    return {
      statistics: { total: results.length, average: avg, highest: max, lowest: min, passRate: (passed / results.length) * 100 },
      insights: response.choices[0].message.content,
      topPerformers: results.sort((a, b) => Number(b.percentage) - Number(a.percentage)).slice(0, 5).map((r) => ({
        name: `${r.student.user.firstName} ${r.student.user.lastName}`,
        score: r.percentage,
        grade: r.grade,
      })),
    };
  }

  // ─── Performance Predictor ────────────────────────────────────────────────────
  async predictPerformance(schoolId: string, studentId: string) {
    const enabled = await this.isModuleEnabled(schoolId, 'performance-predictor');
    if (!enabled) return { error: 'AI Performance Predictor is not enabled' };

    const student = await this.prisma.student.findFirst({
      where: { id: studentId, schoolId },
      include: {
        user: { select: { firstName: true, lastName: true } },
        grades: { orderBy: { createdAt: 'desc' }, take: 20, include: { subject: { select: { name: true } } } },
        attendance: { orderBy: { date: 'desc' }, take: 60 },
      },
    });

    if (!student) return { error: 'Student not found' };

    const avgGrade = student.grades.length > 0
      ? student.grades.reduce((sum, g) => sum + (Number(g.score) / Number(g.maxScore)) * 100, 0) / student.grades.length
      : 0;

    const attendanceRate = student.attendance.length > 0
      ? (student.attendance.filter((a) => ['PRESENT', 'LATE'].includes(a.status)).length / student.attendance.length) * 100
      : 0;

    const gradeBySubject = student.grades.reduce((acc, g) => {
      const subj = g.subject?.name || 'Unknown';
      if (!acc[subj]) acc[subj] = [];
      acc[subj].push((Number(g.score) / Number(g.maxScore)) * 100);
      return acc;
    }, {} as Record<string, number[]>);

    const subjectAverages = Object.entries(gradeBySubject).map(([subject, scores]) => ({
      subject,
      average: (scores as number[]).reduce((a, b) => a + b, 0) / (scores as number[]).length,
    }));

    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 600,
      messages: [
        { role: 'system', content: 'You are an educational AI that predicts student academic performance. Be concise and constructive.' },
        {
          role: 'user',
          content: `Predict performance for student ${student.user.firstName} ${student.user.lastName}:
Overall average: ${avgGrade.toFixed(1)}%
Attendance rate: ${attendanceRate.toFixed(1)}%
Subject performance: ${subjectAverages.map((s) => `${s.subject}: ${s.average.toFixed(1)}%`).join(', ')}

Provide: 1) Performance prediction 2) Risk factors 3) Recommended interventions`,
        },
      ],
    });

    return {
      studentName: `${student.user.firstName} ${student.user.lastName}`,
      currentAverage: avgGrade,
      attendanceRate,
      subjectPerformance: subjectAverages,
      riskLevel: avgGrade < 40 ? 'high' : avgGrade < 60 ? 'medium' : 'low',
      prediction: response.choices[0].message.content,
    };
  }

  // ─── Report Writer ───────────────────────────────────────────────────────────
  async generateStudentReport(schoolId: string, studentId: string, termId: string) {
    const enabled = await this.isModuleEnabled(schoolId, 'report-writer');
    if (!enabled) return { error: 'AI Report Writer is not enabled' };

    const student = await this.prisma.student.findFirst({
      where: { id: studentId, schoolId },
      include: {
        user: { select: { firstName: true, lastName: true, gender: true } },
        grades: { where: { termId }, include: { subject: { select: { name: true } } } },
        attendance: { where: { termId } },
        enrollments: { where: { isCurrent: true }, include: { classRoom: { select: { name: true } } } },
      },
    });

    if (!student) return { error: 'Student not found' };

    const avgGrade = student.grades.length > 0
      ? student.grades.reduce((sum, g) => sum + (Number(g.score) / Number(g.maxScore)) * 100, 0) / student.grades.length
      : 0;

    const attendanceRate = student.attendance.length > 0
      ? (student.attendance.filter((a) => a.status === 'PRESENT').length / student.attendance.length) * 100
      : 0;

    const pronoun = student.user.gender === 'FEMALE' ? 'She' : 'He';

    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 500,
      messages: [
        { role: 'system', content: `You write professional, encouraging school reports for students. Use ${pronoun.toLowerCase()}/${pronoun === 'She' ? 'her' : 'his'} pronouns. Be specific and constructive.` },
        {
          role: 'user',
          content: `Write a terminal report for ${student.user.firstName} ${student.user.lastName} in ${student.enrollments[0]?.classRoom?.name || 'class'}.
Academic average: ${avgGrade.toFixed(1)}%
Attendance: ${attendanceRate.toFixed(1)}%
Subject grades: ${student.grades.map((g) => `${g.subject.name}: ${((Number(g.score) / Number(g.maxScore)) * 100).toFixed(0)}%`).join(', ')}

Write 3 paragraphs: academic performance, attendance/behavior, and areas for improvement/encouragement.`,
        },
      ],
    });

    return {
      studentName: `${student.user.firstName} ${student.user.lastName}`,
      classRoom: student.enrollments[0]?.classRoom?.name,
      averageScore: avgGrade,
      attendanceRate,
      report: response.choices[0].message.content,
    };
  }


  // ─── Fee Defaulter Prediction ────────────────────────────────────────────────
  async predictFeeDefaulters(schoolId: string) {
    const enabled = await this.isModuleEnabled(schoolId, 'fee-defaulter-predictor');
    if (!enabled) return { error: 'Fee Defaulter Predictor is not enabled' };

    const students = await this.prisma.student.findMany({
      where: { schoolId },
      include: {
        user: { select: { firstName: true, lastName: true } },
        invoices: { orderBy: { createdAt: 'desc' }, take: 5 },
      },
    });

    const riskStudents = students
      .map(s => {
        const unpaid = s.invoices.filter(i => ['UNPAID', 'OVERDUE'].includes(i.status)).length;
        const total = s.invoices.length;
        const riskScore = total > 0 ? (unpaid / total) * 100 : 0;
        return { studentId: s.id, name: `${s.user?.firstName} ${s.user?.lastName}`, riskScore: riskScore.toFixed(1), unpaidCount: unpaid, totalInvoices: total };
      })
      .filter(s => s.riskScore > 30)
      .sort((a, b) => Number(b.riskScore) - Number(a.riskScore));

    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 400,
      messages: [{
        role: 'user',
        content: `Based on this fee payment data for ${riskStudents.length} at-risk students, provide a brief summary and 3 actionable recommendations for the school finance team: ${JSON.stringify(riskStudents.slice(0, 5))}`,
      }],
    });

    return { atRiskStudents: riskStudents, summary: response.choices[0].message.content };
  }

  // ─── Revenue Forecasting ─────────────────────────────────────────────────────
  async forecastRevenue(schoolId: string) {
    const enabled = await this.isModuleEnabled(schoolId, 'fee-defaulter-predictor');
    if (!enabled) return { error: 'AI Finance module is not enabled' };

    const monthlyRevenue = await Promise.all(
      Array.from({ length: 6 }, (_, i) => {
        const d = new Date(); d.setMonth(d.getMonth() - i);
        const start = new Date(d.getFullYear(), d.getMonth(), 1);
        const end = new Date(d.getFullYear(), d.getMonth() + 1, 0);
        return this.prisma.payment.aggregate({
          where: { schoolId, status: 'COMPLETED', createdAt: { gte: start, lte: end } },
          _sum: { amount: true },
        }).then(r => ({ month: start.toLocaleString('default', { month: 'short', year: 'numeric' }), amount: Number(r._sum.amount || 0) }));
      })
    );

    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 500,
      messages: [{
        role: 'user',
        content: `Analyze this 6-month revenue data and forecast the next 3 months with confidence levels. Data: ${JSON.stringify(monthlyRevenue.reverse())}. Return JSON: { forecast: [{month, projected, confidence}], trend, recommendation }`,
      }],
    });

    let forecast;
    try { forecast = JSON.parse(response.choices[0].message.content || '{}'); } catch { forecast = { raw: response.choices[0].message.content }; }
    return { historicalData: monthlyRevenue, forecast };
  }

  // ─── Admin Report Writer ─────────────────────────────────────────────────────
  async generateAdminReport(schoolId: string, data: { type: string; period?: string; context?: string }) {
    const enabled = await this.isModuleEnabled(schoolId, 'report-writer');
    if (!enabled) return { error: 'AI Report Writer is not enabled' };

    const school = await this.prisma.school.findUnique({ where: { id: schoolId }, select: { name: true } });
    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 1000,
      messages: [{
        role: 'user',
        content: `Write a professional ${data.type} report for ${school?.name} school for ${data.period || 'the current period'}. Context: ${data.context || 'standard school report'}. Include an executive summary, key findings, and recommendations. Format with clear sections.`,
      }],
    });
    return { report: response.choices[0].message.content, type: data.type };
  }

  // ─── Email/SMS Generator ─────────────────────────────────────────────────────
  async generateCommunication(schoolId: string, data: { type: 'email' | 'sms' | 'announcement'; purpose: string; audience: string; tone?: string }) {
    const enabled = await this.isModuleEnabled(schoolId, 'report-writer');
    if (!enabled) return { error: 'AI Report Writer is not enabled' };

    const school = await this.prisma.school.findUnique({ where: { id: schoolId }, select: { name: true } });
    const maxTokens = data.type === 'sms' ? 200 : 600;
    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: maxTokens,
      messages: [{
        role: 'user',
        content: `Write a ${data.tone || 'professional'} ${data.type} for ${school?.name} school. Purpose: ${data.purpose}. Audience: ${data.audience}. ${data.type === 'sms' ? 'Keep it under 160 characters.' : 'Format appropriately for the channel.'}`,
      }],
    });
    return { content: response.choices[0].message.content, type: data.type };
  }

  // ─── Chat Assistant ──────────────────────────────────────────────────────────
  async chat(schoolId: string, data: { messages: Array<{ role: string; content: string }>; context?: string }) {
    const enabled = await this.isModuleEnabled(schoolId, 'chat-assistant');
    if (!enabled) return { error: 'AI Chat Assistant is not enabled' };

    const response = await this.openai.chat.completions.create({
      model: 'gpt-4o-mini',
      max_tokens: 800,
      messages: [
        {
          role: 'system',
          content: `You are EduCore AI, a helpful assistant for school administration. ${data.context || ''}`,
        },
        ...data.messages.map((m) => ({ role: m.role as any, content: m.content })),
      ],
    });

    return { reply: response.choices[0].message.content };
  }
}

@ApiTags('AI') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'ai', version: '1' })
export class AiController {
  constructor(private readonly aiService: AiService) {}

  @Get('modules') @RequirePermissions('ai:ai:READ')
  getModules(@SchoolId() sid: string) { return this.aiService.getModuleConfigs(sid); }

  @Post('modules/:module/toggle') @RequirePermissions('ai:ai:MANAGE')
  toggleModule(@SchoolId() sid: string, @Param('module') module: string, @Body() body: { isEnabled: boolean; config?: any }) {
    return this.aiService.toggleModule(sid, module, body.isEnabled, body.config);
  }

  @Post('tutor') @RequirePermissions('ai:ai:READ')
  askTutor(@SchoolId() sid: string, @Body() body: { question: string; subject?: string; level?: string }) {
    return this.aiService.askTutor(sid, body);
  }

  @Post('questions/generate') @RequirePermissions('ai:ai:READ')
  generateQuestions(@SchoolId() sid: string, @Body() body: any) {
    return this.aiService.generateQuestions(sid, body);
  }

  @Post('lesson-plan') @RequirePermissions('ai:ai:READ')
  generateLessonPlan(@SchoolId() sid: string, @Body() body: any) {
    return this.aiService.generateLessonPlan(sid, body);
  }

  @Get('analyze-results/:examinationId') @RequirePermissions('ai:ai:READ')
  analyzeResults(@SchoolId() sid: string, @Param('examinationId') id: string) {
    return this.aiService.analyzeResults(sid, id);
  }

  @Get('predict/:studentId') @RequirePermissions('ai:ai:READ')
  predictPerformance(@SchoolId() sid: string, @Param('studentId') id: string) {
    return this.aiService.predictPerformance(sid, id);
  }

  @Get('student-report/:studentId') @RequirePermissions('ai:ai:READ')
  generateReport(@SchoolId() sid: string, @Param('studentId') id: string, @Query('termId') termId: string) {
    return this.aiService.generateStudentReport(sid, id, termId);
  }


  @Post('fee-defaulters') @RequirePermissions('ai:ai:READ')
  predictDefaulters(@SchoolId() sid: string) { return this.aiService.predictFeeDefaulters(sid); }

  @Get('revenue-forecast') @RequirePermissions('ai:ai:READ')
  forecastRevenue(@SchoolId() sid: string) { return this.aiService.forecastRevenue(sid); }

  @Post('admin-report') @RequirePermissions('ai:ai:READ')
  generateAdminReport(@SchoolId() sid: string, @Body() body: any) { return this.aiService.generateAdminReport(sid, body); }

  @Post('generate-communication') @RequirePermissions('ai:ai:READ')
  generateCommunication(@SchoolId() sid: string, @Body() body: any) { return this.aiService.generateCommunication(sid, body); }

  @Post('chat') @RequirePermissions('ai:ai:READ')
  chat(@SchoolId() sid: string, @Body() body: any) {
    return this.aiService.chat(sid, body);
  }
}

@Module({ controllers: [AiController], providers: [AiService], exports: [AiService] })
export class AiModule {}
