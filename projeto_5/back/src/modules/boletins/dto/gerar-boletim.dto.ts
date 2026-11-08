import { ArrayNotEmpty, IsArray, IsEnum } from 'class-validator';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';

const SECAO_INVALIDA = 'Escolha ao menos uma seção válida';

// RN-009 #2 and #3. Repeated sections are accepted once (PR-022 d).
export class GerarBoletimDto {
  /** Seções do boletim, em qualquer ordem */
  @IsArray({ message: SECAO_INVALIDA })
  @ArrayNotEmpty({ message: SECAO_INVALIDA })
  @IsEnum(SecaoBoletim, { each: true, message: SECAO_INVALIDA })
  secoes!: SecaoBoletim[];
}
