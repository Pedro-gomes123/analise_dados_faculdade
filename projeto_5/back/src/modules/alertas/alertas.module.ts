import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AlertaController } from '@/modules/alertas/controllers/alerta.controller';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { AlertaService } from '@/modules/alertas/services/alerta.service';

// MOD-002.
@Module({
  imports: [TypeOrmModule.forFeature([Alerta])],
  controllers: [AlertaController],
  providers: [AlertaService],
})
export class AlertasModule {}
