import { defineConfig } from "vite";
import { resolve } from "path";

const assets = resolve(__dirname, "ckanext/files/assets");

export default defineConfig({
    publicDir: false,
    plugins: [
        {
            name: "prepend-semicolon",
            generateBundle(options, bundle) {
                for (const chunk of Object.values(bundle)) {
                    if (chunk.type === "chunk") {
                        chunk.code = ";" + chunk.code + "\n";
                    }
                }
            },
        },
    ],

    build: {
        lib: {
            entry: resolve(assets, "ts/main.ts"),
            formats: ["iife"],
            fileName: (format) => `script.js`,
            name: "files",
        },
        outDir: resolve(assets),
        emptyOutDir: false,
    },
});
