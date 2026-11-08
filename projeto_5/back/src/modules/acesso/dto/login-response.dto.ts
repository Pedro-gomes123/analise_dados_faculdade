import { UsuarioResponseDto } from '@/modules/acesso/dto/usuario-response.dto';

export class LoginResponseDto {
  /** JWT para o header Authorization: Bearer (DEC-013) */
  access_token!: string;
  usuario!: UsuarioResponseDto;
}
