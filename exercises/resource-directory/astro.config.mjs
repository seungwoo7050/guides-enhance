import { defineConfig } from "astro/config";
import react from "@astrojs/react";

// [Implementation 0]
// The site is prerendered by default. React is enabled only for one isolated browser widget.
export default defineConfig({
  site: "https://resource-directory.example",
  integrations: [react()],
  trailingSlash: "always",
  build: {
    format: "directory"
  }
});
