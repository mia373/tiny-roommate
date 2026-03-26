<p align="center">
  <img src="assets/tinyroommate-logo.svg" width="120" height="120" alt="TinyRoommate" />
</p>

<h1 align="center">TinyRoommate</h1>

<p align="center">
  <strong>A tiny AI companion that lives on your desktop, sees your screen, and remembers you.</strong>
</p>

<!-- TODO: replace with demo GIF
<p align="center">
  <img src="assets/demo.gif" width="480" alt="TinyRoommate demo" />
</p>
-->

---

You open the app. A small cat appears on your desktop. It walks around, sits down, yawns. Every few minutes, a speech bubble pops up — sometimes random (*"~♪"*), sometimes surprisingly relevant (*"you've been coding since 9am... take a break?"*).

You can pet it. Talk to it. Or just let it be.

It sees your screen. It remembers your habits. It writes a diary about you. It gets sad if you ignore it.

It's not an assistant. It's a companion.

<br/>

<table>
<tr>
<td width="50%">

**👀 It sees what you see**<br/>
Screen capture + Claude Vision. It knows if you're coding, designing, or doom-scrolling.

**🧠 It remembers you**<br/>
A living memory that grows over time. Not a stateless chatbot.

</td>
<td width="50%">

**💬 It has personality**<br/>
Sassy, chill, philosophical — you configure it. Knows when to shut up.

**❤️ It needs you**<br/>
Hearts decay over time. Ignore it → sad. Pet it → purrs. Neglect it → sick.

**🔒 100% local**<br/>
All data stays on your machine. Memories, screen captures, journals — nothing leaves your laptop.

</td>
</tr>
</table>

<br/>

## Characters

<p align="center">
  <img src="assets/previews/tabby_cat.gif" width="128" alt="Tabby Cat" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/previews/golden_retriever.gif" width="128" alt="Golden Retriever" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/previews/blue_buddy.gif" width="128" alt="Blue Buddy" />
</p>
<p align="center">
  <sub><strong>Tabby Cat</strong> · <strong>Golden Retriever</strong> · <strong>Blue Buddy</strong></sub><br/>
  <sub>Create your own — see <a href="#add-a-character">Add a Character</a></sub>
</p>

## Getting Started

You need [Node.js](https://nodejs.org/) (v18+), [Rust](https://rustup.rs/), and [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (for the AI brain).

```bash
git clone https://github.com/ryannli/tinyroommate.git
cd tinyroommate
npm install
npx tauri dev
```

First launch takes 2-3 min (Rust compilation). After that it's instant.

> **No Claude Code?** The pet still runs — it walks, fidgets, and reacts to clicks — but it can't think, talk, or see your screen. Install Claude Code to unlock its full brain.

### Screen Recording (optional, macOS)

For the pet to "see" your screen, grant permission in **System Settings → Privacy & Security → Screen Recording** for your terminal app, then restart it.

Without this, everything still works — it just can't see what you're doing.

## Make It Yours

Right-click your pet → **Settings** to change its name, your name, and which character to use.

For deeper customization, edit `.pet-data/config.md`:

```markdown
---
owner_name: Alex
sprite: golden_retriever
---

# Personality
- Be sarcastic and dry
- If I'm working past midnight, roast me

# Health Reminders
- Remind me to take breaks every 30 minutes
- Remind me to drink water every hour
```

Your pet reads this every time it "thinks." Changes take effect immediately.

## Interactions

| | |
|---|---|
| **Hold** mouse on pet | It purrs ❤️ |
| **Click** | Quick reaction |
| **Double-click** | Chat with it |
| **Drag** | Move it around |
| **Right-click** | Settings |

## Its Memory

Your pet keeps a memory in `.pet-data/` — all plain Markdown files you can read:

| File | What it is |
|------|-----------|
| `config.md` | Your preferences — edit this! |
| `me-identity.md` | Its name, species, personality |
| `me-journal.md` | Its diary. It's writing about you. |
| `owner-memory.md` | What it knows about you |
| `owner-perceptions.md` | What it saw on your screen today |
| `owner-timeline.md` | Daily activity summaries over time |

## Add a Character

1. Generate a spritesheet following [SPRITE-SPEC.md](SPRITE-SPEC.md) and process it:

   ```bash
   python3 scripts/process-spritesheet-v3.py your_character.png \
     -o public/sprites/your_character.png \
     --cols 8 --rows 9 --target 128
   ```

2. Add an entry to `src/characters.js`:

   ```js
   // In CHARACTERS:
   your_character: { defaultName: 'Name', displayName: 'Your Character' },

   // In VOICE:
   your_character: {
     greet: '👋',
     acks: ['~♪', '😊', 'hehe', 'hey!', '💛'],
     petHold: 'hehe~ 😊',
     petLines: ['hehe~', 'more...', 'nice~ 😊', "don't stop~"],
     petFallback: 'hehe~ 😊',
     tapLines: ['hm?', '!', 'hey?', '~'],
     tapFallback: 'hey?',
     chatFallback: 'hmm?',
   },
   ```

That's it — the character picker UI is generated automatically.

## License

MIT
