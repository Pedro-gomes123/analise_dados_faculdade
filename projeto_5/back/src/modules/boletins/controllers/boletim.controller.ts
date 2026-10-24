import {
  Body,
  Controller,
  HttpCode,
  HttpStatus,
  Post,
  Res,
} from '@nestjs/common';
import {
  ApiBearerAuth,
  ApiOkResponse,
  ApiProduces,
  ApiTags,
} from '@nestjs/swagger';
import type { Response } from 'express';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { GerarBoletimDto } from '@/modules/boletins/dto/gerar-boletim.dto';
import { BoletimService } from '@/modules/boletins/services/boletim.service';

@ApiTags('boletins')
@ApiBearerAuth()
@Controller('boletins')
export class BoletimController {
  constructor(private readonly boletins: BoletimService) {}

  // PER-012. RN-009. POST because the body carries the sections; nothing is saved.
  // The content type is set only on success (not with @Header), so errors stay JSON.
  @Post('pre-visualizacao')
  @HttpCode(HttpStatus.OK)
  @Papeis(Papel.Tecnico, Papel.Comunicacao)
  @ApiProduces('text/html')
  @ApiOkResponse({ description: 'Boletim em HTML', type: String })
  async preVisualizar(
    @Body() dto: GerarBoletimDto,
    @Res({ passthrough: true }) res: Response,
  ): Promise<string> {
    const html = await this.boletins.preVisualizar(dto.secoes);
    res.type('html');
    return html;
  }
}
