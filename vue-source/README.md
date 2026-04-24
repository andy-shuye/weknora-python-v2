# Lumen AI — Vue 3 + Element Plus Source Structure

Companion source files to the HTML prototype (`Lumen AI.html`). These are reference `.vue` files showing how the prototype translates to a real Vue 3 + Element Plus codebase.

## Stack

- **Vue 3** (Composition API, `<script setup>`)
- **Element Plus** — `ep-` components used: `el-button`, `el-input`, `el-form`, `el-menu`, `el-scrollbar`, `el-avatar`, `el-tag`, `el-dropdown`, `el-dialog`, `el-tabs`, `el-table`, `el-tooltip`
- **Vue Router 4** — screen routing
- **Pinia** — auth + tweaks store
- **Vite** — build
- **SCSS** — design tokens

## Project tree

```
src/
├── main.ts                  Bootstrap + register Element Plus
├── App.vue                  Root — chooses Login vs. AppShell
├── router/index.ts          Routes for /chat /kb /search /agents /spaces /settings
├── stores/
│   ├── auth.ts              Login state
│   └── tweaks.ts            sidebarCollapsed / chatDensity / showCitations
├── styles/
│   ├── tokens.scss          Design tokens (mirrors tokens.css)
│   └── element-overrides.scss   Override Element Plus CSS variables
├── components/
│   ├── LumenMark.vue        Brand logo
│   ├── AppSidebar.vue       Collapsible nav
│   ├── Citation.vue         Citation card
│   ├── CitationInline.vue   Inline [1] reference
│   ├── Composer.vue         Chat input with KB chips
│   ├── KBCard.vue           Knowledge base grid card
│   ├── DocumentRow.vue      File row in KB detail
│   └── TweaksPanel.vue      Edit-mode panel
└── views/
    ├── LoginView.vue
    ├── ChatView.vue
    ├── KBListView.vue
    ├── KBDetailView.vue
    ├── SearchView.vue
    ├── AgentsView.vue
    ├── SpacesView.vue
    └── SettingsView.vue
```

## Element Plus override strategy

Override `--el-color-primary` to the Lumen accent so all EP components align:

```scss
:root {
  --el-color-primary: oklch(0.62 0.09 165);
  --el-color-primary-light-3: oklch(0.75 0.07 165);
  --el-color-primary-light-5: oklch(0.85 0.05 165);
  --el-color-primary-light-7: oklch(0.92 0.03 165);
  --el-color-primary-light-9: oklch(0.97 0.02 165);
  --el-border-radius-base: 8px;
  --el-font-family: 'Manrope', 'Noto Sans SC', system-ui, sans-serif;
  --el-bg-color: #faf8f3;
  --el-text-color-primary: #1a1d26;
}
```

## Running

```bash
pnpm install
pnpm dev
```

See the individual `.vue` files for component implementations.
