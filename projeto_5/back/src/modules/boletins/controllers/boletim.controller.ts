import {
  Body,
  Controller,
  HttpCode,
  HttpStatus,
  Post,
  Res,
  StreamableFile,
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

// PER-012. RN-009. POST because the body carries the sections; nothing is saved.
// Content type is set only on success (not with @Header), so errors stay JSON.
@ApiTags('boletins')
@ApiBearerAuth()
@Controller('boletins')
export class BoletimController {
  constructor(private readonly boletins: BoletimService) {}

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

  // RN-009 #4. Manual publication afterwards (AM-005 b).
  @Post('pdf')
  @HttpCode(HttpStatus.OK)
  @Papeis(Papel.Tecnico, Papel.Comunicacao)
  @ApiProduces('application/pdf')
  @ApiOkResponse({
    description: 'Boletim em PDF',
    schema: { type: 'string', format: 'binary' },
  })
  async gerarPdf(@Body() dto: GerarBoletimDto): Promise<StreamableFile> {
    const pdf = await this.boletins.gerarPdf(dto.secoes);
    return new StreamableFile(pdf.conteudo, {
      type: 'application/pdf',
      disposition: `attachment; filename="${pdf.nome}"`,
      length: pdf.conteudo.length,
    });
  }
}
