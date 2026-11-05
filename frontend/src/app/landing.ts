// The public product page at "/" is for the live demo only. A self-hosted installation
// (ADR-017) is used by one business's own staff, so its image builds with
// VITE_DEMO_MODE=false and "/" keeps sending signed-out visitors to the login screen.
// The decision is made at build time so the page renders without waiting for the API,
// which may be asleep on the free host.
export function showLanding(): boolean {
  return import.meta.env.DEV || import.meta.env.VITE_DEMO_MODE === 'true'
}
