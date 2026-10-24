import { Controller, Get, Query } from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { PeriodoQueryDto, validarPeriodo } from '@/core/dto/periodo-query.dto';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { TempoAcionamentoResponseDto } from '@/modules/rastreio-operacional/dto/tempo-acionamento-response.dto';
import { TempoAcionamentoService } from '@/modules/rastreio-operacional/services/tempo-acionamento.service';

@ApiTags('indicadores')
@ApiBearerAuth()
@Controller('indicadores')
export class IndicadorController {
  constructor(private readonly tempoAcionamento: TempoAcionamentoService) {}

  // PER-009 (EST-03). RN-006.
  @Get('tempo-acionamento')
  @Papeis(Papel.GestaoInstitucional)
  calcularTempoAcionamento(
    @Query() periodo: PeriodoQueryDto,
  ): Promise<TempoAcionamentoResponseDto> {
    validarPeriodo(periodo);
    return this.tempoAcionamento.calcular(periodo);
  }
}
