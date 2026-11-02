import { createBrowserRouter, Navigate } from 'react-router'
import { ApprovalsPage } from '../pages/ApprovalsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage } from '../pages/LoginPage'
import { TicketPage } from '../pages/TicketPage'
import { TicketsPage } from '../pages/TicketsPage'
import { AppShell } from './AppShell'
import { RequireAuth } from './RequireAuth'

export const routes = [
  { path: '/login', element: <LoginPage /> },
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
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]

export const createRouter = () => createBrowserRouter(routes)
