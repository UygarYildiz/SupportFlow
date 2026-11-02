# Design

The operations console for NovaShop support staff. Its job: let an employee decide **quickly and safely** on AI-drafted replies and AI-proposed order changes, and always see what the AI used and what the store rules said.

## Research notes

- E-commerce helpdesks (e.g. Gorgias with Shopify) show order context in a panel **beside the conversation**, and let agents act on orders from there.
- Human-in-the-loop guidance converges on: the AI prepares a **draft that never sends itself**, the draft stays editable, and a human owns the moment where outside-world consequences begin. Approving twice must do nothing.

SupportFlow follows both: conversation and AI draft in the main column, order and decisions in the side column, and every order change behind an explicit approval.

## Concept: a dispatch desk

The visual language comes from parcel paperwork, the world the requests are about:

| Thing | Treatment | Why |
|---|---|---|
| Order | A **shipping label**: heavy ink border, near-square corners, order number large | It is the physical object the customer is asking about |
| AI output | A **carbon-copy draft**: dashed frame, pale blue-grey paper, "Draft by AI" tag | Dashed means "not final"; it must read as a suggestion, never as a fact |
| Proposed change | A label with the change shown as current vs. new | The decision is about one concrete difference |
| Decision | A **rubber stamp** (APPROVED / REJECTED / BLOCKED / EXPIRED) pressed onto the label | The one memorable element; it marks the moment of consequence |
| Waiting proposal | Amber offset shadow behind the label | Pending work stands out without another badge |

Everything else stays quiet: one typeface for the interface, plain sentence-case copy, left alignment, no decorative gradients or card shadows.

## Tokens

| Name | Value | Use |
|---|---|---|
| Ink | `#1C2B3A` | Text, label borders |
| Paper | `#EEF1F4` | App background (cool, not cream) |
| Sheet | `#FFFFFF` | Surfaces |
| Rule | `#CBD3DC` | Dividers |
| Carbon | `#F3F5FA` / `#8494AD` | AI draft background / dashed frame |
| Route teal | `#0F6B73` | Links, primary actions, focus |
| Stamp green / red / amber | `#1E7B4F` / `#B42318` / `#A15C07` | Applied / rejected or blocked / waiting |

Defined in `frontend/src/styles/tokens.css`. Radius follows hierarchy: labels 3px, sheets 8px, controls 6px.

**Type:** Atkinson Hyperlegible for the whole interface (designed for legibility; its distinct letterforms keep order numbers unambiguous). Big Shoulders Stencil Display only for the wordmark and the stamp. Scale 13 / 14 / 16 / 20 / 26 px; tabular figures everywhere.

## Layout

```
┌────────┬────────────────────────────────────┬──────────────────────┐
│ rail   │ Ticket title, status, actions                             │
│        ├────────────────────────────────────┬──────────────────────┤
│Tickets │ Customer message                   │ Proposed change      │
│Approv. │ ┌ ─ Suggested reply (draft) ─ ─ ─┐ │ (label + decision)   │
│        │   summary, warnings, edit, copy    │ Order (label)        │
│        │ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ │ Store policy         │
│ user   │ History                            │                      │
└────────┴────────────────────────────────────┴──────────────────────┘
```

Below 1024px the columns merge in decision order: message, draft, proposal, order, policy, history. Below 760px the rail becomes a top bar.

## Behaviour rules

- AI output is always labelled as a draft; facts it relied on are listed ("Based on ORD-1001"), warnings are shown, not hidden.
- Approve and Reject are disabled while a decision is in flight; a 409 shows the server's reason and the card refreshes to the real state.
- Roles that may not decide see why, not a disabled mystery button.
- The only animation is the stamp press (260ms), triggered by the user's decision; it is off with `prefers-reduced-motion`.
- Keyboard: visible focus ring, skip link, real buttons and links; status changes announced via `role="status"` / `role="alert"`.

## Open for revision

This is the first pass, built before owner review. Likely candidates: the login page's empty right side, density of the ticket table, and whether the draft editor should sit above the summary.
