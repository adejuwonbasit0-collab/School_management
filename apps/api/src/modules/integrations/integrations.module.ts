import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Body, Param, Query, Req, UseGuards, HttpCode } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions } from '../../decorators/permissions.decorator';
import { DatabaseModule } from '../../database/database.module';
import * as crypto from 'crypto';

@Injectable()
class IntegrationsService {
  constructor(private prisma: PrismaService) {}

  // ── API Keys ────────────────────────────────────────────────────────────

  async getApiKeys(schoolId: string) {
    return this.prisma.apiKey.findMany({
      where: { schoolId },
      select: { id: true, name: true, keyPrefix: true, permissions: true, expiresAt: true, lastUsedAt: true, isActive: true, createdAt: true },
      orderBy: { createdAt: 'desc' },
    });
  }

  async createApiKey(schoolId: string, userId: string, dto: { name: string; permissions: string[]; expiresAt?: string }) {
    const rawKey = `ek_${crypto.randomBytes(32).toString('hex')}`;
    const keyHash = crypto.createHash('sha256').update(rawKey).digest('hex');
    const keyPrefix = rawKey.slice(0, 12);

    const apiKey = await this.prisma.apiKey.create({
      data: {
        schoolId,
        name: dto.name,
        keyHash,
        keyPrefix,
        permissions: dto.permissions,
        expiresAt: dto.expiresAt ? new Date(dto.expiresAt) : undefined,
        createdBy: userId,
      },
    });

    return { ...apiKey, rawKey }; // Only time raw key is returned
  }

  async revokeApiKey(id: string, schoolId: string) {
    const key = await this.prisma.apiKey.findFirst({ where: { id, schoolId } });
    if (!key) throw new NotFoundException('API key not found');
    return this.prisma.apiKey.update({ where: { id }, data: { isActive: false } });
  }

  async deleteApiKey(id: string, schoolId: string) {
    const key = await this.prisma.apiKey.findFirst({ where: { id, schoolId } });
    if (!key) throw new NotFoundException('API key not found');
    return this.prisma.apiKey.delete({ where: { id } });
  }

  // ── Webhooks ────────────────────────────────────────────────────────────

  async getWebhooks(schoolId: string) {
    return this.prisma.webhookEndpoint.findMany({
      where: { schoolId },
      include: { _count: { select: { deliveries: true } } },
      orderBy: { createdAt: 'desc' },
    });
  }

  async createWebhook(schoolId: string, dto: { name: string; url: string; events: string[]; secret?: string }) {
    const secret = dto.secret || crypto.randomBytes(20).toString('hex');
    return this.prisma.webhookEndpoint.create({
      data: { schoolId, ...dto, secret },
    });
  }

  async updateWebhook(id: string, schoolId: string, dto: any) {
    const wh = await this.prisma.webhookEndpoint.findFirst({ where: { id, schoolId } });
    if (!wh) throw new NotFoundException('Webhook not found');
    return this.prisma.webhookEndpoint.update({ where: { id }, data: dto });
  }

  async deleteWebhook(id: string, schoolId: string) {
    const wh = await this.prisma.webhookEndpoint.findFirst({ where: { id, schoolId } });
    if (!wh) throw new NotFoundException('Webhook not found');
    return this.prisma.webhookEndpoint.delete({ where: { id } });
  }

  async getWebhookDeliveries(webhookId: string, schoolId: string) {
    const wh = await this.prisma.webhookEndpoint.findFirst({ where: { id: webhookId, schoolId } });
    if (!wh) throw new NotFoundException('Webhook not found');
    return this.prisma.webhookDelivery.findMany({
      where: { webhookId },
      orderBy: { createdAt: 'desc' },
      take: 50,
    });
  }

  async testWebhook(id: string, schoolId: string) {
    const wh = await this.prisma.webhookEndpoint.findFirst({ where: { id, schoolId } });
    if (!wh) throw new NotFoundException('Webhook not found');

    const payload = { event: 'webhook.test', data: { timestamp: new Date().toISOString(), webhookId: id } };
    const signature = crypto.createHmac('sha256', wh.secret || '').update(JSON.stringify(payload)).digest('hex');

    try {
      const response = await fetch(wh.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-EduCore-Signature': signature },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(10000),
      });

      await this.prisma.webhookDelivery.create({
        data: { webhookId: id, event: 'webhook.test', payload, responseCode: response.status, status: response.ok ? 'SUCCESS' : 'FAILED', deliveredAt: new Date(), attempts: 1 },
      });
      return { success: response.ok, status: response.status };
    } catch (err: any) {
      await this.prisma.webhookDelivery.create({
        data: { webhookId: id, event: 'webhook.test', payload, status: 'FAILED', attempts: 1, responseBody: err.message },
      });
      return { success: false, error: err.message };
    }
  }

  // ── Third-Party Integrations ────────────────────────────────────────────

  async getIntegrations(schoolId: string) {
    const existing = await this.prisma.integration.findMany({ where: { schoolId } });
    const providers = [
      { provider: 'google_workspace', name: 'Google Workspace', icon: '🔵', description: 'Sync calendars, drive, and meet' },
      { provider: 'microsoft365', name: 'Microsoft 365', icon: '🟦', description: 'Teams, OneDrive, and Outlook integration' },
      { provider: 'zoom', name: 'Zoom', icon: '🎥', description: 'Schedule and join virtual classes' },
      { provider: 'twilio', name: 'Twilio SMS', icon: '📱', description: 'Send SMS notifications worldwide' },
      { provider: 'sendgrid', name: 'SendGrid', icon: '📧', description: 'Transactional email delivery' },
      { provider: 'mailgun', name: 'Mailgun', icon: '📬', description: 'Developer-friendly email service' },
      { provider: 'termii', name: 'Termii', icon: '📲', description: 'African SMS and messaging platform' },
      { provider: 'paystack', name: 'Paystack', icon: '💳', description: 'Payment processing for Africa' },
      { provider: 'flutterwave', name: 'Flutterwave', icon: '🌊', description: 'Pan-African payment gateway' },
      { provider: 'stripe', name: 'Stripe', icon: '⚡', description: 'Global payment processing' },
    ];

    return providers.map(p => {
      const integration = existing.find(e => e.provider === p.provider);
      return { ...p, isActive: integration?.isActive || false, isConnected: !!integration, integrationId: integration?.id };
    });
  }

  async upsertIntegration(schoolId: string, provider: string, config: any, isActive: boolean) {
    return this.prisma.integration.upsert({
      where: { schoolId_provider: { schoolId, provider } },
      create: { schoolId, provider, name: provider, config, isActive },
      update: { config, isActive },
    });
  }

  async getIntegrationConfig(schoolId: string, provider: string) {
    const integration = await this.prisma.integration.findUnique({ where: { schoolId_provider: { schoolId, provider } } });
    if (!integration) throw new NotFoundException('Integration not found');
    return integration;
  }

  async getStats(schoolId: string) {
    const [apiKeys, webhooks, integrations] = await Promise.all([
      this.prisma.apiKey.count({ where: { schoolId, isActive: true } }),
      this.prisma.webhookEndpoint.count({ where: { schoolId, isActive: true } }),
      this.prisma.integration.count({ where: { schoolId, isActive: true } }),
    ]);
    return { activeApiKeys: apiKeys, activeWebhooks: webhooks, activeIntegrations: integrations };
  }
}

@Controller('integrations')
@UseGuards(JwtAuthGuard, PermissionsGuard)
class IntegrationsController {
  constructor(private readonly svc: IntegrationsService) {}

  @Get('stats') @RequirePermissions('integrations:integrations:READ') stats(@Req() r: any) { return this.svc.getStats(r.user.schoolId); }

  @Get('api-keys') @RequirePermissions('integrations:integrations:READ') getKeys(@Req() r: any) { return this.svc.getApiKeys(r.user.schoolId); }
  @Post('api-keys') @RequirePermissions('integrations:integrations:CREATE') createKey(@Req() r: any, @Body() b: any) { return this.svc.createApiKey(r.user.schoolId, r.user.id, b); }
  @Delete('api-keys/:id') @RequirePermissions('integrations:integrations:DELETE') deleteKey(@Param('id') id: string, @Req() r: any) { return this.svc.deleteApiKey(id, r.user.schoolId); }
  @Put('api-keys/:id/revoke') @RequirePermissions('integrations:integrations:UPDATE') @HttpCode(200) revokeKey(@Param('id') id: string, @Req() r: any) { return this.svc.revokeApiKey(id, r.user.schoolId); }

  @Get('webhooks') @RequirePermissions('integrations:integrations:READ') getWebhooks(@Req() r: any) { return this.svc.getWebhooks(r.user.schoolId); }
  @Post('webhooks') @RequirePermissions('integrations:integrations:CREATE') createWebhook(@Req() r: any, @Body() b: any) { return this.svc.createWebhook(r.user.schoolId, b); }
  @Put('webhooks/:id') @RequirePermissions('integrations:integrations:UPDATE') updateWebhook(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.svc.updateWebhook(id, r.user.schoolId, b); }
  @Delete('webhooks/:id') @RequirePermissions('integrations:integrations:DELETE') deleteWebhook(@Param('id') id: string, @Req() r: any) { return this.svc.deleteWebhook(id, r.user.schoolId); }
  @Get('webhooks/:id/deliveries') @RequirePermissions('integrations:integrations:READ') getDeliveries(@Param('id') id: string, @Req() r: any) { return this.svc.getWebhookDeliveries(id, r.user.schoolId); }
  @Post('webhooks/:id/test') @RequirePermissions('integrations:integrations:UPDATE') @HttpCode(200) testWebhook(@Param('id') id: string, @Req() r: any) { return this.svc.testWebhook(id, r.user.schoolId); }

  @Get('providers') @RequirePermissions('integrations:integrations:READ') getProviders(@Req() r: any) { return this.svc.getIntegrations(r.user.schoolId); }
  @Put('providers/:provider') @RequirePermissions('integrations:integrations:UPDATE') upsertIntegration(@Param('provider') p: string, @Req() r: any, @Body() b: any) {
    return this.svc.upsertIntegration(r.user.schoolId, p, b.config, b.isActive);
  }
  @Get('providers/:provider/config') @RequirePermissions('integrations:integrations:READ') getConfig(@Param('provider') p: string, @Req() r: any) {
    return this.svc.getIntegrationConfig(r.user.schoolId, p);
  }
}

@Module({
  imports: [DatabaseModule],
  controllers: [IntegrationsController],
  providers: [IntegrationsService],
  exports: [IntegrationsService],
})
export class IntegrationsModule {}
