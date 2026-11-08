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
import { ApiBearerAuth, ApiConflictResponse, ApiTags } from '@nestjs/swagger';
import { ApiPaginationQuery, Paginate, Paginated } from 'nestjs-paginate';
import type { PaginateQuery } from 'nestjs-paginate';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { AlterarUsuarioDto } from '@/modules/acesso/dto/alterar-usuario.dto';
import { CriarUsuarioDto } from '@/modules/acesso/dto/criar-usuario.dto';
import { UsuarioResponseDto } from '@/modules/acesso/dto/usuario-response.dto';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import {
  USUARIO_PAGINATE_CONFIG,
  UsuarioService,
} from '@/modules/acesso/services/usuario.service';

// Invalid :id is 422 like any other invalid input (DEC-010).
const IdPipe = new ParseIntPipe({
  errorHttpStatusCode: HttpStatus.UNPROCESSABLE_ENTITY,
});

// PER-003: administrator only.
@ApiTags('usuarios')
@ApiBearerAuth()
@Papeis(Papel.Administrador)
@Controller('usuarios')
export class UsuarioController {
  constructor(private readonly usuarios: UsuarioService) {}

  @Get()
  @ApiPaginationQuery(USUARIO_PAGINATE_CONFIG)
  async listar(
    @Paginate() query: PaginateQuery,
  ): Promise<Paginated<UsuarioResponseDto>> {
    const pagina = await this.usuarios.listar(query);
    return {
      ...pagina,
      data: pagina.data.map((usuario) => UsuarioResponseDto.from(usuario)),
    } as Paginated<UsuarioResponseDto>;
  }

  @Get(':id')
  async buscar(@Param('id', IdPipe) id: number): Promise<UsuarioResponseDto> {
    return UsuarioResponseDto.from(await this.usuarios.buscarPorId(id));
  }

  @Post()
  @ApiConflictResponse({ description: 'EMAIL_JA_CADASTRADO' })
  async criar(@Body() dto: CriarUsuarioDto): Promise<UsuarioResponseDto> {
    return UsuarioResponseDto.from(await this.usuarios.criar(dto));
  }

  @Patch(':id')
  async alterar(
    @Param('id', IdPipe) id: number,
    @Body() dto: AlterarUsuarioDto,
  ): Promise<UsuarioResponseDto> {
    return UsuarioResponseDto.from(await this.usuarios.alterar(id, dto));
  }
}
