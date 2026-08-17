import { Module } from '@nestjs/common';
import { Controller, Get, Post, Put, Delete, Body, Param, Query, Req, UseGuards } from '@nestjs/common';
import { InventoryService } from './inventory.service';
import { JwtAuthGuard } from '../../guards/jwt-auth.guard';
import { DatabaseModule } from '../../database/database.module';

@Controller('inventory')
@UseGuards(JwtAuthGuard)
class InventoryController {
  constructor(private readonly inventoryService: InventoryService) {}

  @Get('stats') stats(@Req() r: any) { return this.inventoryService.getInventoryStats(r.user.schoolId); }
  @Get('low-stock') lowStock(@Req() r: any) { return this.inventoryService.getLowStockItems(r.user.schoolId); }

  @Get('categories') getCategories(@Req() r: any) { return this.inventoryService.getCategories(r.user.schoolId); }
  @Post('categories') createCategory(@Req() r: any, @Body() b: any) { return this.inventoryService.createCategory(r.user.schoolId, b.name); }

  @Get('suppliers') getSuppliers(@Req() r: any) { return this.inventoryService.getSuppliers(r.user.schoolId); }
  @Post('suppliers') createSupplier(@Req() r: any, @Body() b: any) { return this.inventoryService.createSupplier(r.user.schoolId, b); }
  @Put('suppliers/:id') updateSupplier(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.inventoryService.updateSupplier(id, r.user.schoolId, b); }

  @Get('items') getItems(@Req() r: any, @Query() q: any) { return this.inventoryService.getItems(r.user.schoolId, q); }
  @Get('items/:id') getItem(@Param('id') id: string, @Req() r: any) { return this.inventoryService.getItem(id, r.user.schoolId); }
  @Post('items') createItem(@Req() r: any, @Body() b: any) { return this.inventoryService.createItem(r.user.schoolId, b); }
  @Put('items/:id') updateItem(@Param('id') id: string, @Req() r: any, @Body() b: any) { return this.inventoryService.updateItem(id, r.user.schoolId, b); }
  @Delete('items/:id') deleteItem(@Param('id') id: string, @Req() r: any) { return this.inventoryService.deleteItem(id, r.user.schoolId); }

  @Get('items/:id/transactions') getTx(@Param('id') id: string, @Req() r: any) { return this.inventoryService.getTransactions(id, r.user.schoolId); }
  @Post('items/:id/transactions') recordTx(@Param('id') id: string, @Req() r: any, @Body() b: any) {
    return this.inventoryService.recordTransaction(id, r.user.schoolId, r.user.id, b);
  }
}

@Module({
  imports: [DatabaseModule],
  controllers: [InventoryController],
  providers: [InventoryService],
  exports: [InventoryService],
})
export class InventoryModule {}
