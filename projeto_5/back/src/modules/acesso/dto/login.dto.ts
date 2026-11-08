import { IsEmail, IsNotEmpty, IsString, MaxLength } from 'class-validator';

export class LoginDto {
  /** E-mail do usuário */
  @IsEmail({}, { message: 'E-mail inválido' })
  @MaxLength(254)
  email!: string;

  /** Senha */
  @IsString()
  @IsNotEmpty({ message: 'Senha obrigatória' })
  senha!: string;
}
