import {
  Body,
  Controller,
  Get,
  HttpStatus,
  Param,
  ParseIntPipe,
  Patch,
  Post,
} from '@nestjs/common';
import { ApiBearerAuth, ApiNotFoundResponse, ApiTags } from '@nestjs/swagger';
import { ApiPaginationQuery, Paginate, Paginated } from 'nestjs-paginate';
import type { PaginateQuery } from 'nestjs-paginate';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { UsuarioAtual } from '@/modules/acesso/decorators/usuario-atual.decorator';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { AlterarParametroAlertaDto } from '@/modules/alertas/dto/alterar-parametro-alerta.dto';
import { CriarParametroAlertaDto } from '@/modules/alertas/dto/criar-parametro-alerta.dto';
import {
  ParametroAlertaHistoricoResponseDto,
  ParametroAlertaResponseDto,
} from '@/modules/alertas/dto/parametro-alerta-response.dto';
import {
  HISTORICO_PAGINATE_CONFIG,
  PARAMETRO_ALERTA_PAGINATE_CONFIG,
  ParametroAlertaService,
} from '@/modules/alertas/services/parametro-alerta.service';

// Invalid :id is 422 like any other invalid input (DEC-010).
const IdPipe = new ParseIntPipe({
  errorHttpStatusCode: HttpStatus.UNPROCESSABLE_ENTITY,
});

// No DELETE: parameters are only deactivated (DEC-014).
@ApiTags('parametros-alerta')
@ApiBearerAuth()
@Controller('parametros-alerta')
export class ParametroAlertaController {
  constructor(private readonly parametros: ParametroAlertaService) {}

  // PER-004: the technician only reads (PR-008).
  @Get()
  @Papeis(Papel.Tecnico, Papel.Gestor)
  @ApiPaginationQuery(PARAMETRO_ALERTA_PAGINATE_CONFIG)
  async listar(
    @Paginate() query: PaginateQuery,
  ): Promise<Paginated<ParametroAlertaResponseDto>> {
    const pagina = await this.parametros.listar(query);
    return {
      ...pagina,
      data: pagina.data.map((p) => ParametroAlertaResponseDto.from(p)),
    } as Paginated<ParametroAlertaResponseDto>;
  }

  // PER-004. RN-001.
  @Get(':id/historico')
  @Papeis(Papel.Tecnico, Papel.Gestor)
  @ApiPaginationQuery(HISTORICO_PAGINATE_CONFIG)
  @ApiNotFoundResponse({ description: 'Parâmetro não encontrado' })
  async historico(
    @Param('id', IdPipe) id: number,
    @Paginate() query: PaginateQuery,
  ): Promise<Paginated<ParametroAlertaHistoricoResponseDto>> {
    const pagina = await this.parametros.historico(id, query);
    return {
      ...pagina,
      data: pagina.data.map((h) => ParametroAlertaHistoricoResponseDto.from(h)),
    } as Paginated<ParametroAlertaHistoricoResponseDto>;
  }

  // PER-005.
  @Post()
  @Papeis(Papel.Gestor)
  async criar(
    @Body() dto: CriarParametroAlertaDto,
    @UsuarioAtual() usuario: Usuario,
  ): Promise<ParametroAlertaResponseDto> {
    return ParametroAlertaResponseDto.from(
      await this.parametros.criar(dto, usuario),
    );
  }

  // PER-005. Includes deactivation (ativo: false).
  @Patch(':id')
  @Papeis(Papel.Gestor)
  @ApiNotFoundResponse({ description: 'Parâmetro não encontrado' })
  async alterar(
    @Param('id', IdPipe) id: number,
    @Body() dto: AlterarParametroAlertaDto,
    @UsuarioAtual() usuario: Usuario,
  ): Promise<ParametroAlertaResponseDto> {
    return ParametroAlertaResponseDto.from(
      await this.parametros.alterar(id, dto, usuario),
    );
  }
}
