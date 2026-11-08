import { Transform } from 'class-transformer';
import {
  IsNotEmpty,
  IsNumber,
  IsString,
  Max,
  MaxLength,
  Min,
} from 'class-validator';

const trim = ({ value }: { value: unknown }) =>
  typeof value === 'string' ? value.trim() : value;

// decimal(12,3) in the database (erd.md).
const LIMIAR_MAX = 999_999_999.999;

export class CriarParametroAlertaDto {
  /** Variável de gold.leitura_climatica (DEC-009) */
  @Transform(trim)
  @IsString({ message: 'Variável inválida' })
  @IsNotEmpty({ message: 'Variável inválida' })
  @MaxLength(50, { message: 'Variável inválida' })
  variavel!: string;

  /** Identificador do território (granularidade: DUV-009) */
  @Transform(trim)
  @IsString({ message: 'Território inválido' })
  @IsNotEmpty({ message: 'Território inválido' })
  @MaxLength(50, { message: 'Território inválido' })
  territorio!: string;

  /** Valor de referência da variável (comparação: DUV-010) */
  @IsNumber({ maxDecimalPlaces: 3 }, { message: 'Limiar obrigatório' })
  @Min(-LIMIAR_MAX, { message: 'Limiar fora do intervalo' })
  @Max(LIMIAR_MAX, { message: 'Limiar fora do intervalo' })
  limiar!: number;

  /** Nível de risco do alerta (escala: DUV-010) */
  @Transform(trim)
  @IsString({ message: 'Nível inválido' })
  @IsNotEmpty({ message: 'Nível inválido' })
  @MaxLength(20, { message: 'Nível inválido' })
  nivel!: string;
}
