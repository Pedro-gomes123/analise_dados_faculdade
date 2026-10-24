import { AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { http } from '@/lib/http'
import { setToken } from '@/modules/auth/session'

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
