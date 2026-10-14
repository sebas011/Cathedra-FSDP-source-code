import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";

const releaseVersion = readFileSync(new URL("../VERSION", import.meta.url), "utf-8").trim();
const product = readFileSync(new URL("../APP_PRODUCT", import.meta.url), "utf-8").trim();
if (product !== "fsdp") throw new Error("Invalid Cathedra product");

export default defineConfig({
  plugins: [react(), {
    name: "cathedra-release-version",
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "release-version.txt", source: releaseVersion });
    },
  }],
  define: {
    "import.meta.env.VITE_CATHEDRA_VERSION": JSON.stringify(releaseVersion),
    "import.meta.env.VITE_CATHEDRA_PRODUCT": JSON.stringify(product),
  },
  server: {
    host: "127.0.0.1",
    port: 5174,
    strictPort: true,
  },
});
