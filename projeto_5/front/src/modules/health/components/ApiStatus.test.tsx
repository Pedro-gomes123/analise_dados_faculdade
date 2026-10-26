import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiStatus } from '@/modules/health/components/ApiStatus'
import { getHealth } from '@/modules/health/service/health.service'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/health/service/health.service', () => ({
  getHealth: vi.fn(),
}))

const getHealthMock = vi.mocked(getHealth)

describe('ApiStatus', () => {
  beforeEach(() => {
    getHealthMock.mockReset()
  })

  it('shows a loading message while checking', () => {
    getHealthMock.mockReturnValue(new Promise(() => {}))
    renderWithQuery(<ApiStatus />)

    expect(screen.getByText('Verificando a API...')).toBeInTheDocument()
  })

  it('shows success when the API and database are up', async () => {
    getHealthMock.mockResolvedValue({ status: 'ok', info: { database: { status: 'up' } } })
    renderWithQuery(<ApiStatus />)

    expect(await screen.findByText('API e banco de dados funcionando.')).toBeInTheDocument()
  })

  it('shows an error with retry when the request fails', async () => {
    getHealthMock.mockRejectedValueOnce(new Error('Network Error'))
    getHealthMock.mockResolvedValueOnce({ status: 'ok' })
    renderWithQuery(<ApiStatus />)

    expect(await screen.findByRole('alert')).toHaveTextContent('API indisponível.')

    await userEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(await screen.findByText('API e banco de dados funcionando.')).toBeInTheDocument()
    expect(getHealthMock).toHaveBeenCalledTimes(2)
  })
})
