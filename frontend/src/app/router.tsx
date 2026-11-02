import { createBrowserRouter, Navigate } from 'react-router'
import { ApprovalsPage } from '../pages/ApprovalsPage'
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
      { index: true, element: <Navigate to="/tickets" replace /> },
      { path: '/tickets', element: <TicketsPage /> },
      { path: '/tickets/:ticketId', element: <TicketPage /> },
      { path: '/approvals', element: <ApprovalsPage /> },
      { path: '*', element: <Navigate to="/tickets" replace /> },
    ],
  },
]

export const createRouter = () => createBrowserRouter(routes)
