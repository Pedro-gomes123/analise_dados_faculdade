import { Transform } from 'class-transformer';
import {
  ArrayMinSize,
  IsArray,
  IsEmail,
  IsEnum,
  IsNotEmpty,
  IsString,
  MaxLength,
  MinLength,
} from 'class-validator';
import { Papel } from '@/modules/acesso/enums/papel.enum';

const trim = ({ value }: { value: unknown }) =>
  typeof value === 'string' ? value.trim() : value;

export const SENHA_MIN = 8;

export class CriarUsuarioDto {
  /** Nome completo */
  @Transform(trim)
  @IsString()
  @IsNotEmpty({ message: 'Nome obrigatório' })
  @MaxLength(150)
  nome!: string;

  /** E-mail, único no sistema (RN-010) */
  @IsEmail({}, { message: 'E-mail inválido' })
  @MaxLength(254)
  email!: string;

  /** Senha inicial, definida pelo administrador (PR-020) */
  @IsString()
  @MinLength(SENHA_MIN, {
    message: `A senha precisa ter ao menos ${SENHA_MIN} caracteres`,
  })
  @MaxLength(128)
  senha!: string;

  /** Um ou mais papéis (AM-004 c) */
  @IsArray()
  @ArrayMinSize(1, { message: 'Informe ao menos um papel válido' })
  @IsEnum(Papel, { each: true, message: 'Informe ao menos um papel válido' })
  papeis!: Papel[];
}
