# @resilio/desktop

Tauri 2.x desktop wrapper of `apps/web` (Next.js) — Windows + macOS.

## Prerequisites

### All platforms
- **Node.js** ≥ 20 + **pnpm** ≥ 10
- **Rust** toolchain — install via [rustup.rs](https://rustup.rs/)
  ```bash
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  ```

### Windows (additional)
- **Microsoft C++ Build Tools** (VS Build Tools 2019+) — required by Rust on Windows
  - Download: [visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  - Install workload: "Desktop development with C++"
- **WebView2 Runtime** — included in Windows 11; download for older Windows:
  [developer.microsoft.com/microsoft-edge/webview2/](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)

### macOS (additional)
- **Xcode Command Line Tools**: `xcode-select --install`

---

## Development

From monorepo root — starts Next.js dev server and Tauri dev window together:

```bash
pnpm dev:desktop
```

This runs:
1. `pnpm dev:web` — Next.js at http://localhost:3000
2. `wait-on tcp:3000` then `tauri dev` — Tauri dev window loading from localhost

---

## Production Build

From monorepo root:

```bash
pnpm build:desktop
```

This:
1. `pnpm --filter @resilio/web build:static` — Next.js static export → `apps/web/out/`
2. `pnpm --filter @resilio/desktop build` — Tauri bundles (`.msi` / `.dmg`)

Output: `apps/desktop/src-tauri/target/release/bundle/`

---

## Code Signing

**Not configured.** Development builds are unsigned.

To distribute signed builds:
- **Windows**: Set `TAURI_PRIVATE_KEY` + `TAURI_KEY_PASSWORD` env vars, configure `bundle.windows.certificateThumbprint` in `tauri.conf.json`
- **macOS**: Configure `bundle.macOS.signingIdentity` and `bundle.macOS.providerShortName`, requires Apple Developer account

---

## Architecture

```
apps/desktop/
├── src-tauri/
│   ├── tauri.conf.json   Tauri 2.x config (productName=Resilio+, id=com.resilio.plus)
│   ├── Cargo.toml        Rust deps: tauri 2, tauri-plugin-opener, serde
│   ├── build.rs
│   ├── icons/            Placeholder icons — replace before signed distribution
│   └── src/
│       ├── main.rs       Entry point
│       └── lib.rs        Tauri builder (invoke_handler, plugins)
└── package.json
```

Dev mode loads from `http://localhost:3000` (Next.js dev server).  
Prod mode loads from static files at `apps/web/out/` (Next.js static export).
