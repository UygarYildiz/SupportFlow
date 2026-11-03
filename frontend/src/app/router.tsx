import { createBrowserRouter, Navigate } from 'react-router'
import { AccountPage } from '../pages/AccountPage'
import { ApprovalsPage } from '../pages/ApprovalsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage } from '../pages/LoginPage'
import { SetupPage } from '../pages/SetupPage'
import { TeamPage } from '../pages/TeamPage'
import { TicketPage } from '../pages/TicketPage'
import { TicketsPage } from '../pages/TicketsPage'
import { AppShell } from './AppShell'
import { RequireAdmin, RequireAuth } from './RequireAuth'

export const routes = [
  { path: '/login', element: <LoginPage /> },
  { path: '/setup', element: <SetupPage /> },
  {
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: '/tickets', element: <TicketsPage /> },
      { path: '/tickets/:ticketId', element: <TicketPage /> },
      { path: '/approvals', element: <ApprovalsPage /> },
      {
        path: '/team',
        element: (
          <RequireAdmin>
            <TeamPage />
          </RequireAdmin>
        ),
      },
      { path: '/account', element: <AccountPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]

export const createRouter = () => createBrowserRouter(routes)
