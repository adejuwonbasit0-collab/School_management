import { Module } from '@nestjs/common';
import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { Controller, Get, Post, Put, Body, Param, Query, UseGuards } from '@nestjs/common';
import { PrismaService } from '../../database/prisma.service';
import { JwtAuthGuard, PermissionsGuard } from '../../guards/jwt-auth.guard';
import { RequirePermissions, SchoolId } from '../../decorators/current-user.decorator';
import { ApiTags, ApiBearerAuth } from '@nestjs/swagger';

@Injectable()
export class HostelService {
  constructor(private readonly prisma: PrismaService) {}

  async getRooms(hostelId: string) {
    return this.prisma.hostelRoom.findMany({
      where: { hostelId },
      include: { allocations: { where: { status: 'ACTIVE' } } },
      orderBy: { name: 'asc' },
    });
  }

  async vacateResident(id: string) {
    return this.prisma.hostelAllocation.update({
      where: { id },
      data: { status: 'VACATED', endDate: new Date() },
    });
  }

  async getHostels(schoolId: string) { return this.prisma.hostel.findMany({ where: { schoolId }, include: { _count: { select: { rooms: true } }, rooms: { include: { _count: { select: { residents: true } } } } } }); }
  async createHostel(schoolId: string, data: any) { return this.prisma.hostel.create({ data: { schoolId, name: data.name, type: data.type, capacity: data.capacity } }); }
  async addRoom(hostelId: string, data: any) { return this.prisma.hostelRoom.create({ data: { hostelId, roomNo: data.roomNo, type: data.type, capacity: data.capacity, floor: data.floor, fee: data.fee } }); }
  async assignResident(data: any) {
    const room = await this.prisma.hostelRoom.findUnique({ where: { id: data.roomId }, include: { _count: { select: { residents: true } } } });
    if (!room) throw new NotFoundException('Room not found');
    if (room._count.residents >= room.capacity) throw new BadRequestException('Room is at full capacity');
    return this.prisma.hostelResident.upsert({ where: { studentId: data.studentId }, create: { studentId: data.studentId, roomId: data.roomId, checkInDate: new Date(data.checkInDate) }, update: { roomId: data.roomId, checkInDate: new Date(data.checkInDate), checkOutDate: null } });
  }
  async getResidents(schoolId: string) { return this.prisma.hostelResident.findMany({ where: { room: { hostel: { schoolId } }, checkOutDate: null }, include: { student: { include: { user: { select: { firstName: true, lastName: true } } } }, room: { include: { hostel: { select: { name: true } } } } } }); }
}

@ApiTags('Hostel') @ApiBearerAuth('JWT-auth')
@UseGuards(JwtAuthGuard, PermissionsGuard)
@Controller({ path: 'hostel', version: '1' })
export class HostelController {
  constructor(private readonly service: HostelService) {}

  @Get('allocations') @RequirePermissions('hostel:hostel:READ') getAllocations(@SchoolId() sid: string) { return this.service.getResidents(sid); }
  @Post('allocations') @RequirePermissions('hostel:hostel:UPDATE') createAllocation(@Body() d: any) { return this.service.assignResident(d); }
  @Put('allocations/:id/vacate') @RequirePermissions('hostel:hostel:UPDATE') vacate(@Param('id') id: string) { return this.service.vacateResident(id); }
  @Get(':id/rooms') @RequirePermissions('hostel:hostel:READ') getRooms(@Param('id') hid: string) { return this.service.getRooms(hid); }

  @Get() @RequirePermissions('hostel:hostel:READ') getHostels(@SchoolId() sid: string) { return this.service.getHostels(sid); }
  @Post() @RequirePermissions('hostel:hostel:CREATE') createHostel(@SchoolId() sid: string, @Body() d: any) { return this.service.createHostel(sid, d); }
  @Post(':id/rooms') @RequirePermissions('hostel:hostel:CREATE') addRoom(@Param('id') id: string, @Body() d: any) { return this.service.addRoom(id, d); }
  @Post('residents') @RequirePermissions('hostel:hostel:UPDATE') assignResident(@Body() d: any) { return this.service.assignResident(d); }
  @Get('residents') @RequirePermissions('hostel:hostel:READ') getResidents(@SchoolId() sid: string) { return this.service.getResidents(sid); }
}

@Module({ controllers: [HostelController], providers: [HostelService], exports: [HostelService] })
export class HostelModule {}
