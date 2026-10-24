import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { AcaoController } from '@/modules/rastreio-operacional/controllers/acao.controller';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';
import { AcaoService } from '@/modules/rastreio-operacional/services/acao.service';

// MOD-003.
@Module({
  imports: [TypeOrmModule.forFeature([Acao, Alerta])],
  controllers: [AcaoController],
  providers: [AcaoService],
})
export class RastreioOperacionalModule {}
