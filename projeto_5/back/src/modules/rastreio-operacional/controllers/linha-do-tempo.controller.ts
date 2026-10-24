import { Controller, Get, Query } from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { PeriodoQueryDto, validarPeriodo } from '@/core/dto/periodo-query.dto';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { LinhaDoTempoResponseDto } from '@/modules/rastreio-operacional/dto/linha-do-tempo-response.dto';
import { LinhaDoTempoService } from '@/modules/rastreio-operacional/services/linha-do-tempo.service';

@ApiTags('linha-do-tempo')
@ApiBearerAuth()
@Controller('linha-do-tempo')
export class LinhaDoTempoController {
  constructor(private readonly linhaDoTempo: LinhaDoTempoService) {}

  // PER-008 (EST-02). RN-005.
  @Get()
  @Papeis(Papel.Gestor, Papel.GestaoInstitucional)
  consultar(
    @Query() periodo: PeriodoQueryDto,
  ): Promise<LinhaDoTempoResponseDto> {
    validarPeriodo(periodo);
    return this.linhaDoTempo.consultar(periodo);
  }
}
