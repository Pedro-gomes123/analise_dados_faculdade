import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { AcaoController } from '@/modules/rastreio-operacional/controllers/acao.controller';
import { IndicadorController } from '@/modules/rastreio-operacional/controllers/indicador.controller';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';
import { AcaoService } from '@/modules/rastreio-operacional/services/acao.service';
import { TempoAcionamentoService } from '@/modules/rastreio-operacional/services/tempo-acionamento.service';

// MOD-003.
@Module({
  imports: [TypeOrmModule.forFeature([Acao, Alerta])],
  controllers: [AcaoController, IndicadorController],
  providers: [AcaoService, TempoAcionamentoService],
})
export class RastreioOperacionalModule {}
