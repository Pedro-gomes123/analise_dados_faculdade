import { FilterOperator } from 'nestjs-paginate';
import { ALERTA_PAGINATE_CONFIG } from '@/modules/alertas/services/alerta.service';

describe('ALERTA_PAGINATE_CONFIG (DEC-012, PR-009)', () => {
  it('lists the newest alerts first', () => {
    expect(ALERTA_PAGINATE_CONFIG.defaultSortBy).toEqual([
      ['dthrDisparo', 'DESC'],
    ]);
  });

  it('filters active or closed alerts and by level', () => {
    expect(ALERTA_PAGINATE_CONFIG.filterableColumns).toMatchObject({
      status: [FilterOperator.EQ],
      nivel: [FilterOperator.EQ, FilterOperator.IN],
    });
  });

  it('caps the page size', () => {
    expect(ALERTA_PAGINATE_CONFIG.maxLimit).toBe(100);
  });
});
