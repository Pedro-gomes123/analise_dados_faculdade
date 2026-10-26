import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import {
  FilterOperator,
  paginate,
  Paginated,
  PaginateConfig,
  PaginateQuery,
} from 'nestjs-paginate';
import { DataSource, Repository } from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import {
  CamposEditaveis,
  diferencaParametro,
} from '@/modules/alertas/domain/diferenca-parametro';
import { ParametroAlertaHistorico } from '@/modules/alertas/entities/parametro-alerta-historico.entity';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { OperacaoHistorico } from '@/modules/alertas/enums/operacao-historico.enum';

export interface CriarParametroAlerta {
  variavel: string;
  territorio: string;
  limiar: number;
  nivel: string;
}

// DEC-012.
export const PARAMETRO_ALERTA_PAGINATE_CONFIG: PaginateConfig<ParametroAlerta> =
  {
    sortableColumns: ['id', 'variavel', 'territorio', 'dthrAtualizacao'],
    defaultSortBy: [
      ['variavel', 'ASC'],
      ['territorio', 'ASC'],
    ],
    filterableColumns: {
      ativo: [FilterOperator.EQ],
      variavel: [FilterOperator.EQ],
      territorio: [FilterOperator.EQ],
    },
    defaultLimit: 20,
    maxLimit: 100,
  };

// DEC-012. Newest change first.
export const HISTORICO_PAGINATE_CONFIG: PaginateConfig<ParametroAlertaHistorico> =
  {
    sortableColumns: ['id', 'dthrCriacao'],
    defaultSortBy: [['dthrCriacao', 'DESC']],
    relations: { usuario: true },
    defaultLimit: 20,
    maxLimit: 100,
  };

@Injectable()
export class ParametroAlertaService {
  constructor(
    @InjectRepository(ParametroAlerta)
    private readonly parametros: Repository<ParametroAlerta>,
    @InjectRepository(ParametroAlertaHistorico)
    private readonly historicos: Repository<ParametroAlertaHistorico>,
    private readonly dataSource: DataSource,
  ) {}

  // RN-001 #1 and #4: parameter and history in the same transaction.
  // The variable is not checked against the gold until DEC-009 exists.
  criar(dados: CriarParametroAlerta, autor: Usuario): Promise<ParametroAlerta> {
    return this.dataSource.transaction(async (manager) => {
      const parametro = await manager.save(
        manager.create(ParametroAlerta, { ...dados, ativo: true }),
      );
      await manager.insert(ParametroAlertaHistorico, {
        idParametroAlerta: parametro.id,
        idUsuario: autor.id,
        operacao: OperacaoHistorico.Criacao,
        valorAnterior: null,
        valorNovo: { ...dados, ativo: true },
      });
      return parametro;
    });
  }

  // RN-001 #2 to #4. The row is locked while the previous value is read, so two
  // concurrent edits each record what they actually replaced.
  alterar(
    id: number,
    dados: Partial<CamposEditaveis>,
    autor: Usuario,
  ): Promise<ParametroAlerta> {
    return this.dataSource.transaction(async (manager) => {
      const parametro = await manager.findOne(ParametroAlerta, {
        where: { id },
        lock: { mode: 'pessimistic_write' },
      });
      if (!parametro) throw new NotFoundException('Parâmetro não encontrado');

      const diferenca = diferencaParametro(parametro, dados);
      if (!diferenca) return parametro;

      Object.assign(parametro, diferenca.novo);
      const salvo = await manager.save(parametro);
      await manager.insert(ParametroAlertaHistorico, {
        idParametroAlerta: id,
        idUsuario: autor.id,
        operacao: diferenca.operacao,
        valorAnterior: diferenca.anterior,
        valorNovo: diferenca.novo,
      });
      return salvo;
    });
  }

  listar(query: PaginateQuery): Promise<Paginated<ParametroAlerta>> {
    return paginate(query, this.parametros, PARAMETRO_ALERTA_PAGINATE_CONFIG);
  }

  async historico(
    id: number,
    query: PaginateQuery,
  ): Promise<Paginated<ParametroAlertaHistorico>> {
    if (!(await this.parametros.exists({ where: { id } }))) {
      throw new NotFoundException('Parâmetro não encontrado');
    }
    return paginate(query, this.historicos, {
      ...HISTORICO_PAGINATE_CONFIG,
      where: { idParametroAlerta: id },
    });
  }
}
