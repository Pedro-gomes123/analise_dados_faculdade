import { AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { describeApiError, http } from '@/lib/http'
import { setToken } from '@/modules/auth/session'
import { apiError } from '@/test/api-error'

async function headersEnviados() {
  let enviado: InternalAxiosRequestConfig | undefined
  await http.get('/qualquer', {
    adapter: (config) => {
      enviado = config
      return Promise.resolve({ data: {}, status: 200, statusText: 'OK', headers: {}, config })
    },
  })
  return AxiosHeaders.from(enviado?.headers)
}

describe('http', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('envia o token no header Authorization (DEC-013)', async () => {
    setToken('jwt')
    expect((await headersEnviados()).get('Authorization')).toBe('Bearer jwt')
  })

  it('não envia Authorization sem token', async () => {
    expect((await headersEnviados()).has('Authorization')).toBe(false)
  })
})

describe('describeApiError', () => {
  it('prefere a mensagem do primeiro campo no 422', () => {
    const erro = apiError(422, {
      message: 'Dados inválidos',
      errors: [{ property: 'senha', constraints: { minLength: 'Senha curta' } }],
    })
    expect(describeApiError(erro)).toBe('Senha curta')
  })

  it('usa a mensagem da regra de negócio', () => {
    const erro = apiError(409, { message: 'Já existe um usuário com este e-mail' })
    expect(describeApiError(erro)).toBe('Já existe um usuário com este e-mail')
  })

  it('não mostra detalhe de erro do servidor', () => {
    expect(describeApiError(apiError(500, { message: 'stack' }))).toBe(
      'Erro inesperado. Tente de novo.',
    )
  })

  it('avisa falha de conexão', () => {
    expect(describeApiError(new Error('Network Error'))).toBe(
      'Não foi possível conectar ao servidor',
    )
  })
})
