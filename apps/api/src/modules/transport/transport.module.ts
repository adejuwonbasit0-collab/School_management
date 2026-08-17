import { Module } from '@nestjs/common';
import { Injectable, NotFoundException } from '@nestjs/common';
import { Controller, Delete, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class TransportService {
  constructor(private readonly prisma: PrismaService) {}

  async deleteRoute(schoolId: string, id: string) {
    return this.prisma.transportRoute.delete({ where: { id } });
  }

  async addPickupPoint(routeId: string, dto: { name: string; time: string; landmark?: string; sequence: number }) {
    // Store pickup points as JSON stops on the route
    const route = await this.prisma.transportRoute.findUnique({ where: { id: routeId } });
    if (!route) throw new Error('Route not found');
    const stops = (route.stops as any[]) || [];
    stops.push({ id: `stop-${Date.now()}`, ...dto });
    stops.sort((a: any, b: any) => a.sequence - b.sequence);
    return this.prisma.transportRoute.update({ where: { id: routeId }, data: { stops: stops as any } });
  }

  async getBuses(schoolId: string) {
    // Buses stored as transport records with type BUS
    return this.prisma.transportRoute.findMany({
      where: { schoolId },
      select: { id: true, vehicle: true, driver: true, driverPhone: true },
    }).then(routes => routes.filter(r => r.vehicle).map(r => ({ id: r.id, plateNumber: r.vehicle, model: r.vehicle, driver: r.driver })));
  }

  async addBus(schoolId: string, dto: any) {
    return this.prisma.transportRoute.create({ data: { schoolId, name: dto.plateNumber, vehicle: dto.plateNumber, driver: dto.driverName, stops: [] as any } });
  }

  async getDrivers(schoolId: string) {
    return this.prisma.transportRoute.findMany({
      where: { schoolId, driver: { not: null } },
      select: { id: true, driver: true, driverPhone: true },
    }).then(routes => routes.map(r => ({ id: r.id, name: r.driver, phone: r.driverPhone })));
  }

  async getRoutes(schoolId: string) { return this.prisma.transportRoute.findMany({ where: { schoolId }, include: { _count: { select: { students: true } } }, orderBy: { name: 'asc' } }); }
  async getRoute(schoolId: string, id: string) {
    const route = await this.prisma.transportRoute.findFirst({ where: { id, schoolId }, include: { students: { include: { student: { include: { user: { select: { firstName: true, lastName: true } } } } } } } });
    if (!route) throw new NotFoundException('Route not found');
    return route;
  }
  async createRoute(schoolId: string, data: any) { return this.prisma.transportRoute.create({ data: { schoolId, name: data.name, description: data.description, stops: data.stops || [], fee: data.fee, vehicle: data.vehicle, driver: data.driver, driverPhone: data.driverPhone } }); }
  async updateRoute(id: string, data: any) { return this.prisma.transportRoute.update({ where: { id }, data: { name: data.name, description: data.description, stops: data.stops, fee: data.fee, vehicle: data.vehicle, driver: data.driver, driverPhone: data.driverPhone, status: data.status } }); }
  async assignStudent(data: any) { return this.prisma.transportStudent.upsert({ where: { studentId: data.studentId }, create: { studentId: data.studentId, routeId: data.routeId, pickupStop: data.pickupStop, dropStop: data.dropStop }, update: { routeId: data.routeId, pickupStop: data.pickupStop, dropStop: data.dropStop } }); }
}

@ApiTags('Transport') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'transport', version: '1' })
export class TransportController {
  constructor(private readonly service: TransportService) {}

  @Delete('routes/:id') @RequirePermissions('transport:transport:UPDATE') deleteRoute(@SchoolId() sid: string, @Param('id') id: string) { return this.service.deleteRoute(sid, id); }
  @Post('routes/:id/pickup-points') @RequirePermissions('transport:transport:CREATE') addPickup(@Param('id') id: string, @Body() d: any) { return this.service.addPickupPoint(id, d); }
  @Get('routes/:id') @RequirePermissions('transport:transport:READ') getRouteById(@SchoolId() sid: string, @Param('id') id: string) { return this.service.getRoute(sid, id); }
  @Get('buses') @RequirePermissions('transport:transport:READ') getBuses(@SchoolId() sid: string) { return this.service.getBuses(sid); }
  @Post('buses') @RequirePermissions('transport:transport:CREATE') addBus(@SchoolId() sid: string, @Body() d: any) { return this.service.addBus(sid, d); }
  @Get('drivers') @RequirePermissions('transport:transport:READ') getDrivers(@SchoolId() sid: string) { return this.service.getDrivers(sid); }

  @Get('routes') @RequirePermissions('transport:transport:READ') getRoutes(@SchoolId() sid: string) { return this.service.getRoutes(sid); }
  @Get('routes/:id') @RequirePermissions('transport:transport:READ') getRoute(@SchoolId() sid: string, @Param('id') id: string) { return this.service.getRoute(sid, id); }
  @Post('routes') @RequirePermissions('transport:transport:CREATE') createRoute(@SchoolId() sid: string, @Body() d: any) { return this.service.createRoute(sid, d); }
  @Put('routes/:id') @RequirePermissions('transport:transport:UPDATE') updateRoute(@Param('id') id: string, @Body() d: any) { return this.service.updateRoute(id, d); }
  @Post('assign') @RequirePermissions('transport:transport:UPDATE') assignStudent(@Body() d: any) { return this.service.assignStudent(d); }
}

@Module({ controllers: [TransportController], providers: [TransportService], exports: [TransportService] })
export class TransportModule {}
