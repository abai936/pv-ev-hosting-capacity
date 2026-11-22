// @ts-check
import { defineConfig } from 'astro/config';

// Published on GitHub Pages under a sub-path, so every URL must carry the base.
// https://astro.build/config
export default defineConfig({
  site: 'https://abai936.github.io',
  base: '/pv-ev-hosting-capacity',
  trailingSlash: 'always',
});
