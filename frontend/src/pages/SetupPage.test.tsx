import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import { mockApi, renderWithProviders } from '../test/utils'
import { SetupPage } from './SetupPage'

const OPEN = {
  mode: 'self_hosted',
  setup_required: true,
  setup_token_required: true,
  organization_name: null,
}

function renderSetup() {
  return renderWithProviders(
    <Routes>
      <Route path="/setup" element={<SetupPage />} />
      <Route path="/login" element={<p>Giriş sayfası</p>} />
      <Route path="/" element={<p>Genel bakış</p>} />
    </Routes>,
    { route: '/setup' },
  )
}

async function fillForm(password = 'uzun ve güçlü bir parola', again = password) {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('İşletme adı'), 'Kuzey Kırtasiye')
  await user.type(screen.getByLabelText('Adınız ve soyadınız'), 'Deniz Kaya')
  await user.type(screen.getByLabelText('İş e-postası'), 'deniz@kuzey.example')
  await user.type(screen.getByLabelText('Parola'), password)
  await user.type(screen.getByLabelText('Parola (tekrar)'), again)
  await user.type(await screen.findByLabelText('Kurulum kodu'), 'kod-0123456789abcdef')
  await user.click(screen.getByRole('button', { name: 'Kurulumu tamamla' }))
}

describe('SetupPage', () => {
  it('creates the business and its first admin, then opens the workspace', async () => {
    const calls = mockApi((url, init) => {
      if (url.pathname === '/api/v1/setup' && init.method === 'POST') {
        return { status: 201, body: { access_token: 'token', token_type: 'bearer', expires_in: 1800 } }
      }
      return { body: OPEN }
    })
    renderSetup()
    await fillForm()

    expect(await screen.findByText('Genel bakış')).toBeInTheDocument()
    const post = calls.find((c) => c.method === 'POST')
    expect(post?.body).toEqual({
      organization_name: 'Kuzey Kırtasiye',
      full_name: 'Deniz Kaya',
      email: 'deniz@kuzey.example',
      password: 'uzun ve güçlü bir parola',
      setup_token: 'kod-0123456789abcdef',
    })
  })

  it('catches mistyped passwords before sending anything', async () => {
    const calls = mockApi(() => ({ body: OPEN }))
    renderSetup()
    await fillForm('uzun ve güçlü bir parola', 'uzun ve güçlü bir parolа')

    expect(await screen.findByRole('alert')).toHaveTextContent('Parolalar birbirini tutmuyor.')
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
  })

  it('shows the server message for a wrong setup code', async () => {
    mockApi((_url, init) =>
      init.method === 'POST'
        ? { status: 403, body: { detail: 'Kurulum kodu hatalı' } }
        : { body: OPEN },
    )
    renderSetup()
    await fillForm()

    expect(await screen.findByRole('alert')).toHaveTextContent('Kurulum kodu hatalı')
  })

  it('sends a finished installation to the login page', async () => {
    mockApi(() => ({ body: { ...OPEN, setup_required: false, organization_name: 'Kuzey' } }))
    renderSetup()

    expect(await screen.findByText('Giriş sayfası')).toBeInTheDocument()
  })
})
