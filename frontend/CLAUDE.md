# Frontend conventions

Loaded when working under `frontend/`. Project-wide rules are in the root `CLAUDE.md`.

- All HTTP goes through `src/api/client.ts`; components use hooks from `src/api/queries.ts` (TanStack Query) and types from `src/api/types.ts`, which alias the generated `src/api/schema.d.ts`. After changing a backend schema, run `npm run gen:api` and commit the result.
- Visual language and tokens are in `docs/DESIGN.md` and `src/styles/tokens.css`: orders as shipping labels, AI output in the dashed "carbon" draft frame, decisions as the stamp. Use tokens, not raw colors; sentence-case copy; no all-caps labels except the stamp.
- Mutations disable their buttons while pending and invalidate affected queries on settle (a 409 means our copy is stale).
- Tests: `src/test/utils.tsx` provides `mockApi` (fetch router), `renderWithProviders` and a `proposal()` fixture.
- Vite proxies `/api`, `/health` and `/ready` to the backend, so no CORS setup is needed in dev.
- Font gotcha: `@fontsource/big-shoulders-stencil-display` maps `./*` to `./*.css`, so import its weights without `.css` (declared in `src/fonts.d.ts`).
