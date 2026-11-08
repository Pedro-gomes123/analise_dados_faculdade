import { Controller, Get } from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { ApiPaginationQuery, Paginate, Paginated } from 'nestjs-paginate';
import type { PaginateQuery } from 'nestjs-paginate';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { AlertaResponseDto } from '@/modules/alertas/dto/alerta-response.dto';
import {
  ALERTA_PAGINATE_CONFIG,
  AlertaService,
} from '@/modules/alertas/services/alerta.service';

@ApiTags('alertas')
@ApiBearerAuth()
@Controller('alertas')
export class AlertaController {
  constructor(private readonly alertas: AlertaService) {}

  // PER-006. COM pending DUV-036, implemented as denied.
  @Get()
  @Papeis(Papel.Tecnico, Papel.Gestor, Papel.GestaoInstitucional)
  @ApiPaginationQuery(ALERTA_PAGINATE_CONFIG)
  async listar(
    @Paginate() query: PaginateQuery,
  ): Promise<Paginated<AlertaResponseDto>> {
    const pagina = await this.alertas.listar(query);
    return {
      ...pagina,
      data: pagina.data.map((alerta) => AlertaResponseDto.from(alerta)),
    } as Paginated<AlertaResponseDto>;
  }
}
