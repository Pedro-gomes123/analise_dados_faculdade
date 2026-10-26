import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AlertaController } from '@/modules/alertas/controllers/alerta.controller';
import { ParametroAlertaController } from '@/modules/alertas/controllers/parametro-alerta.controller';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { ParametroAlertaHistorico } from '@/modules/alertas/entities/parametro-alerta-historico.entity';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { AlertaService } from '@/modules/alertas/services/alerta.service';
import { ParametroAlertaService } from '@/modules/alertas/services/parametro-alerta.service';

// MOD-002.
@Module({
  imports: [
    TypeOrmModule.forFeature([
      Alerta,
      ParametroAlerta,
      ParametroAlertaHistorico,
    ]),
  ],
  controllers: [AlertaController, ParametroAlertaController],
  providers: [AlertaService, ParametroAlertaService],
})
export class AlertasModule {}
