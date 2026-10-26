import { Body, Controller, Get, Post } from '@nestjs/common';
import { ApiBearerAuth, ApiNotFoundResponse, ApiTags } from '@nestjs/swagger';
import { ApiPaginationQuery, Paginate, Paginated } from 'nestjs-paginate';
import type { PaginateQuery } from 'nestjs-paginate';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { UsuarioAtual } from '@/modules/acesso/decorators/usuario-atual.decorator';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { AcaoResponseDto } from '@/modules/rastreio-operacional/dto/acao-response.dto';
import { CriarAcaoDto } from '@/modules/rastreio-operacional/dto/criar-acao.dto';
import {
  ACAO_PAGINATE_CONFIG,
  AcaoService,
} from '@/modules/rastreio-operacional/services/acao.service';

// No PATCH or DELETE: actions are never edited or removed (RN-004 #5, DEC-014).
@ApiTags('acoes')
@ApiBearerAuth()
@Controller('acoes')
export class AcaoController {
  constructor(private readonly acoes: AcaoService) {}

  // PER-007. GIN pending DUV-036, implemented as denied.
  @Post()
  @Papeis(Papel.Gestor)
  @ApiNotFoundResponse({ description: 'Alerta informado não existe' })
  async criar(
    @Body() dto: CriarAcaoDto,
    @UsuarioAtual() usuario: Usuario,
  ): Promise<AcaoResponseDto> {
    const acao = await this.acoes.criar(
      { descricao: dto.descricao, idAlerta: dto.id_alerta },
      usuario,
    );
    return AcaoResponseDto.from(acao);
  }

  // PER-008.
  @Get()
  @Papeis(Papel.Gestor, Papel.GestaoInstitucional)
  @ApiPaginationQuery(ACAO_PAGINATE_CONFIG)
  async listar(
    @Paginate() query: PaginateQuery,
  ): Promise<Paginated<AcaoResponseDto>> {
    const pagina = await this.acoes.listar(query);
    return {
      ...pagina,
      data: pagina.data.map((acao) => AcaoResponseDto.from(acao)),
    } as Paginated<AcaoResponseDto>;
  }
}
