import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  resolve: {
    /*
     * The ui-kit is installed from a local path, so resolving through its
     * symlink can reach the copy of React in *its* node_modules as well as the
     * app's. Two Reacts means hooks throw at runtime — and the build still
     * succeeds, so nothing catches it until the page is blank. Keep this.
     */
    dedupe: ['react', 'react-dom'],
  },
  // The kit is linked rather than published during development, so Vite is told
  // not to pre-bundle it; edits to the kit show up on the next rebuild.
  optimizeDeps: {
    exclude: ['@insights-platform/ui-kit'],
  },
});
