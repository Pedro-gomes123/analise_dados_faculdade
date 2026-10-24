import { Transform } from 'class-transformer';
import {
  IsInt,
  IsNotEmpty,
  IsOptional,
  IsString,
  MaxLength,
  Min,
} from 'class-validator';

const trim = ({ value }: { value: unknown }) =>
  typeof value === 'string' ? value.trim() : value;

// RN-004 #3: author and time are never accepted from the client (no such fields).
export class CriarAcaoDto {
  /** O que foi feito */
  @Transform(trim)
  @IsString({ message: 'Descreva a ação' })
  @IsNotEmpty({ message: 'Descreva a ação' })
  @MaxLength(2000)
  descricao!: string;

  /** Alerta que motivou a ação (RN-004 #4, RN-006) */
  @IsOptional()
  @IsInt({ message: 'Alerta inválido' })
  @Min(1, { message: 'Alerta inválido' })
  id_alerta?: number;
}
