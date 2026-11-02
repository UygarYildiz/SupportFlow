// The stencil font package maps "./*" to "./*.css", so its weights are imported without
// the extension (see main.tsx); TypeScript needs to know the side-effect module exists.
declare module '@fontsource/big-shoulders-stencil-display/800'
