import { Module } from '@nestjs/common';
import { Injectable } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { EventEmitter2, OnEvent } from '@nestjs/event-emitter';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class AutomationService {
  constructor(private readonly prisma: PrismaService, private readonly events: EventEmitter2) {}

  async getAutomations(schoolId: string) {
    return this.prisma.automation.findMany({ where: { schoolId }, orderBy: { createdAt: 'desc' } });
  }

  async createAutomation(schoolId: string, data: any) {
    return this.prisma.automation.create({ data: { schoolId, name: data.name, description: data.description, trigger: data.trigger, conditions: data.conditions, actions: data.actions, isActive: data.isActive ?? true } });
  }

  async updateAutomation(id: string, data: any) {
    return this.prisma.automation.update({ where: { id }, data: { name: data.name, description: data.description, conditions: data.conditions, actions: data.actions, isActive: data.isActive } });
  }

  async deleteAutomation(id: string) {
    await this.prisma.automation.delete({ where: { id } });
    return { message: 'Automation deleted' };
  }

  async toggleAutomation(id: string, isActive: boolean) {
    return this.prisma.automation.update({ where: { id }, data: { isActive } });
  }

  async executeAutomation(automationId: string, payload: any) {
    const automation = await this.prisma.automation.findUnique({ where: { id: automationId } });
    if (!automation || !automation.isActive) return;
    try {
      // Execute each action
      for (const action of automation.actions as any[]) {
        await this.executeAction(action, payload);
      }
      await this.prisma.automation.update({ where: { id: automationId }, data: { runCount: { increment: 1 }, lastRunAt: new Date() } });
      await this.prisma.automationLog.create({ data: { automationId, success: true, payload } });
    } catch (err) {
      await this.prisma.automationLog.create({ data: { automationId, success: false, error: err.message, payload } });
    }
  }

  private async executeAction(action: any, payload: any) {
    // Action executor - handles different action types
    switch (action.type) {
      case 'SEND_EMAIL':
        this.events.emit('automation.send_email', { ...action.config, payload });
        break;
      case 'SEND_SMS':
        this.events.emit('automation.send_sms', { ...action.config, payload });
        break;
      case 'CREATE_NOTIFICATION':
        this.events.emit('automation.create_notification', { ...action.config, payload });
        break;
      case 'WEBHOOK':
        // Would make HTTP call to webhook URL
        break;
    }
  }

  @OnEvent('student.created')
  async handleStudentCreated(payload: any) {
    const automations = await this.prisma.automation.findMany({ where: { schoolId: payload.schoolId, trigger: 'STUDENT_ENROLLED', isActive: true } });
    for (const auto of automations) await this.executeAutomation(auto.id, payload);
  }

  @OnEvent('finance.payment.completed')
  async handlePaymentCompleted(payload: any) {
    const automations = await this.prisma.automation.findMany({ where: { schoolId: payload.schoolId, trigger: 'FEE_PAID', isActive: true } });
    for (const auto of automations) await this.executeAutomation(auto.id, payload);
  }
}

@ApiTags('Automation') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'automation', version: '1' })
export class AutomationController {
  constructor(private readonly service: AutomationService) {}
  @Get() @RequirePermissions('automation:automation:READ') getAutomations(@SchoolId() sid: string) { return this.service.getAutomations(sid); }
  @Post() @RequirePermissions('automation:automation:CREATE') create(@SchoolId() sid: string, @Body() d: any) { return this.service.createAutomation(sid, d); }
  @Put(':id') @RequirePermissions('automation:automation:UPDATE') update(@Param('id') id: string, @Body() d: any) { return this.service.updateAutomation(id, d); }
  @Delete(':id') @RequirePermissions('automation:automation:DELETE') delete(@Param('id') id: string) { return this.service.deleteAutomation(id); }
  @Put(':id/toggle') @RequirePermissions('automation:automation:UPDATE') toggle(@Param('id') id: string, @Body() body: any) { return this.service.toggleAutomation(id, body.isActive); }
}

@Module({ controllers: [AutomationController], providers: [AutomationService], exports: [AutomationService] })
export class AutomationModule {}
