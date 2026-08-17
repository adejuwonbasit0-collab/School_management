import { Module } from '@nestjs/common';
import { Controller, Get } from '@nestjs/common';
import { TerminusModule, HealthCheck, HealthCheckService, PrismaHealthIndicator, HttpHealthIndicator } from '@nestjs/terminus';
import { ApiTags } from '@nestjs/swagger';
import { PrismaService } from '../../database/prisma.service';
import { Public } from '../../decorators/current-user.decorator';

@ApiTags('Health')
@Controller({ path: 'health', version: '1' })
export class HealthController {
  constructor(private readonly health: HealthCheckService, private readonly prisma: PrismaService) {}

  @Get()
  @Public()
  @HealthCheck()
  check() {
    return { status: 'ok', timestamp: new Date().toISOString(), version: '1.0.0', service: 'EduCore API' };
  }
}

@Module({ imports: [TerminusModule], controllers: [HealthController] })
export class HealthModule {}
