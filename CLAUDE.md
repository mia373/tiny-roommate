# TinyRoommate

An AI desktop companion (pet) built with Tauri + Vite + Claude CLI (Haiku).

## Architecture

- **Frontend**: Vanilla JS (no framework), Vite for bundling
- **Desktop shell**: Tauri v2 (Rust backend at `src-tauri/`)
- **Pet brain**: Claude CLI (Haiku model) invoked as subprocess via `@tauri-apps/plugin-shell`
- **Pet data**: Markdown files with YAML frontmatter, stored at `.pet-data/`

## Key modules (`src/`)

| File | Role |
|------|------|
| `main.js` | Entry point, wires all modules together |
| `brain.js` | LLM calls, file I/O, config loading, frontmatter parsing |
| `behavior.js` | Autonomous behavior loop (2-3 min decision cycle) |
| `signals.js` | Passive signal collection (time, idle, screen capture) |
| `interaction.js` | Mouse/chat/drag input handling |
| `sprite.js` | Spritesheet animation renderer |
| `bubble-manager.js` | Speech bubble window lifecycle |
| `characters.js` | Character voice/text generation |
| `hearts.js` | Floating hearts (affection system) |
| `settings.js` | Settings UI |

## Pet data (`.pet-data/`)

Runtime pet memory — NOT checked into git. Structure:

```
.pet-data/
  CLAUDE.md              # Brain instructions (system prompt for Claude CLI)
  config.md              # Owner preferences (frontmatter: pet_name, owner_name, sprite, born)
  me-identity.md         # Pet's self-description (written by the pet)
  me-journal.md          # Pet's diary
  owner-memory.md        # Accumulated knowledge about owner
  owner-perceptions.md   # Screen captures (updated every 2 min)
  owner-timeline.md      # Daily activity summaries
```

Created automatically on first launch via `seedPetDataIfNeeded()` in `brain.js`.

## Dev commands

```bash
npm install          # Install JS deps
npx tauri dev        # Run in dev mode (first build compiles Rust ~2-3 min)
npm run build        # Build frontend only
```

## Code conventions

- Vanilla JS, no TypeScript, no framework
- `var`/`function` style (intentional, not legacy)
- No classes except `SpriteAnimator`
- Shell commands via `Command.create()` from `@tauri-apps/plugin-shell`
- Config files use YAML frontmatter parsed by `parseFrontmatter()` in `brain.js`
