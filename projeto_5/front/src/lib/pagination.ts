// Resposta paginada do nestjs-paginate (DEC-012).
export interface Paginated<T> {
  data: T[]
  meta: {
    itemsPerPage: number
    totalItems: number
    currentPage: number
    totalPages: number
  }
}
