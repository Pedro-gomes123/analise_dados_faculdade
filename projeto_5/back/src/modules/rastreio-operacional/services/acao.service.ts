import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import {
  FilterOperator,
  paginate,
  Paginated,
  PaginateConfig,
  PaginateQuery,
} from 'nestjs-paginate';
import { Repository } from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';

export interface CriarAcao {
  descricao: string;
  idAlerta?: number;
}

// DEC-012. Newest first; the chronological timeline is RN-005 (TASK-023).
export const ACAO_PAGINATE_CONFIG: PaginateConfig<Acao> = {
  sortableColumns: ['id', 'dthrCriacao'],
  defaultSortBy: [['dthrCriacao', 'DESC']],
  filterableColumns: { idAlerta: [FilterOperator.EQ, FilterOperator.NULL] },
  relations: { usuario: true },
  defaultLimit: 20,
  maxLimit: 100,
};

@Injectable()
export class AcaoService {
  constructor(
    @InjectRepository(Acao) private readonly acoes: Repository<Acao>,
    @InjectRepository(Alerta) private readonly alertas: Repository<Alerta>,
  ) {}

  // RN-004: author is the authenticated user; time is the server's (column default).
  async criar(dados: CriarAcao, autor: Usuario): Promise<Acao> {
    if (
      dados.idAlerta !== undefined &&
      !(await this.alertas.exists({ where: { id: dados.idAlerta } }))
    ) {
      throw new NotFoundException('Alerta não encontrado');
    }

    const salva = await this.acoes.save(
      this.acoes.create({
        descricao: dados.descricao,
        idAlerta: dados.idAlerta ?? null,
        idUsuario: autor.id,
      }),
    );
    return this.buscarPorId(salva.id);
  }

  listar(query: PaginateQuery): Promise<Paginated<Acao>> {
    return paginate(query, this.acoes, ACAO_PAGINATE_CONFIG);
  }

  private async buscarPorId(id: number): Promise<Acao> {
    const acao = await this.acoes.findOne({
      where: { id },
      relations: { usuario: true },
    });
    if (!acao) throw new NotFoundException('Ação não encontrada');
    return acao;
  }
}
