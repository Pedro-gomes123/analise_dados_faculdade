import { SetMetadata } from '@nestjs/common';
import { Papel } from '@/modules/acesso/enums/papel.enum';

export const PAPEIS_KEY = 'papeis';

// Roles allowed on a route (permissoes.md). A user with any of them passes (AM-004 c).
export const Papeis = (...papeis: Papel[]) => SetMetadata(PAPEIS_KEY, papeis);
