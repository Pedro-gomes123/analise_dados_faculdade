import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';

class AutorDto {
  id!: number;
  nome!: string;
}

// API shape of an action (MOD-003 contract, DEC-011).
export class AcaoResponseDto {
  id!: number;
  descricao!: string;
  id_alerta!: number | null;
  autor!: AutorDto;
  registrada_em!: Date;

  static from(acao: Acao): AcaoResponseDto {
    return {
      id: acao.id,
      descricao: acao.descricao,
      id_alerta: acao.idAlerta,
      autor: { id: acao.usuario.id, nome: acao.usuario.nome },
      registrada_em: acao.dthrCriacao,
    };
  }
}
