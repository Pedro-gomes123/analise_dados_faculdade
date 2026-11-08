import { PartialType, PickType } from '@nestjs/swagger';
import { IsBoolean, IsOptional } from 'class-validator';
import { CriarParametroAlertaDto } from '@/modules/alertas/dto/criar-parametro-alerta.dto';

// RN-001 #2: threshold and level change. Variable and territory identify the
// parameter; a different pair is a new parameter.
export class AlterarParametroAlertaDto extends PartialType(
  PickType(CriarParametroAlertaDto, ['limiar', 'nivel'] as const),
) {
  /** false inativa o parâmetro (DEC-014, RN-001 #3) */
  @IsOptional()
  @IsBoolean()
  ativo?: boolean;
}
