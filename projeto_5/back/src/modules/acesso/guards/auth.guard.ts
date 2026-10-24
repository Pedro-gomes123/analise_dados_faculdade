import {
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { JwtService } from '@nestjs/jwt';
import { IS_PUBLIC_KEY } from '@/core/auth/public.decorator';
import { PAPEIS_KEY } from '@/modules/acesso/decorators/papeis.decorator';
import { RequestAutenticada } from '@/modules/acesso/decorators/usuario-atual.decorator';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { JwtPayload } from '@/modules/acesso/services/auth.service';
import { UsuarioService } from '@/modules/acesso/services/usuario.service';

export const NAO_AUTENTICADO_MESSAGE = 'Faça login para continuar';
export const SEM_PERMISSAO_MESSAGE = 'Você não tem permissão para esta ação';

// Global guard (DEC-013, DEC-010): 401 without a valid token or for an inactive
// user, 403 when the route requires roles the user does not have.
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    private readonly jwt: JwtService,
    private readonly usuarios: UsuarioService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const targets = [context.getHandler(), context.getClass()];
    if (this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, targets)) {
      return true;
    }

    const request = context.switchToHttp().getRequest<RequestAutenticada>();
    const token = this.extrairToken(request.headers.authorization);
    if (!token) throw new UnauthorizedException(NAO_AUTENTICADO_MESSAGE);

    const payload = await this.jwt.verifyAsync<JwtPayload>(token).catch(() => {
      throw new UnauthorizedException(NAO_AUTENTICADO_MESSAGE);
    });

    // Loaded on every request so deactivation and role changes apply at once.
    const usuario = await this.usuarios.buscarAutenticado(payload.sub);
    if (!usuario?.ativo)
      throw new UnauthorizedException(NAO_AUTENTICADO_MESSAGE);
    request.usuario = usuario;

    const exigidos = this.reflector.getAllAndOverride<Papel[] | undefined>(
      PAPEIS_KEY,
      targets,
    );
    if (exigidos?.length) {
      const temPapel = usuario.papeis.some((p) => exigidos.includes(p.papel));
      if (!temPapel) throw new ForbiddenException(SEM_PERMISSAO_MESSAGE);
    }

    return true;
  }

  private extrairToken(header: string | undefined): string | undefined {
    const [tipo, token] = header?.split(' ') ?? [];
    return tipo === 'Bearer' && token ? token : undefined;
  }
}
