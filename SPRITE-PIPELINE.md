# Sprite Pipeline

TinyRoommate uses a two-step character asset workflow:

1. Generate a source sprite sheet that matches [Sprite Spec](SPRITE-SPEC.md).
2. Run the repo pipeline below to turn it into an in-app sprite and optional README previews.

## Required

Install the image tooling once:

```bash
python3 -m pip install --user pillow numpy
```

Process the source sheet into the app-ready sprite:

```bash
python3 scripts/process-spritesheet-v4.py path/to/your-character-source.png \
  -o public/sprites/your_character.png \
  --cols 8 --rows 9 --target 128
```

Register the character in `src/characters.js`:

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

Once `public/sprites/your_character.png` exists and the entry is registered, the Settings picker will include the new character automatically.

## Optional Docs Previews

If you want the character to appear in the README preview gallery, generate preview assets from the processed sprite sheet:

```bash
python3 scripts/generate-preview-gif.py public/sprites/your_character.png \
  -o assets/previews/your_character.gif \
  --still-output assets/previews/your_character.png
```

This script expects the cleaned `8x9` sheet produced by `process-spritesheet-v4.py` with `--target 128`.

These preview assets are docs-only:

- `assets/previews/your_character.gif`
- `assets/previews/your_character.png`

The app itself only needs `public/sprites/your_character.png` and the matching registration in `src/characters.js`.
