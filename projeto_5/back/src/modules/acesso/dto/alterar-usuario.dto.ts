import { PartialType, PickType } from '@nestjs/swagger';
import { IsBoolean, IsOptional } from 'class-validator';
import { CriarUsuarioDto } from '@/modules/acesso/dto/criar-usuario.dto';

// E-mail is not editable: it identifies the account (RN-010).
export class AlterarUsuarioDto extends PartialType(
  PickType(CriarUsuarioDto, ['nome', 'senha', 'papeis'] as const),
) {
  /** false inativa o usuário (DEC-014) */
  @IsOptional()
  @IsBoolean()
  ativo?: boolean;
}
