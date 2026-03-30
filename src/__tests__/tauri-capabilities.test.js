import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('default Tauri capability', function() {
  it('grants permissions to all auxiliary windows the app opens', function() {
    var filePath = resolve(process.cwd(), 'src-tauri/capabilities/default.json');
    var capability = JSON.parse(readFileSync(filePath, 'utf8'));

    expect(capability.windows).toEqual(
      expect.arrayContaining(['main', 'bubble', 'settings', 'context-menu', 'chat'])
    );
  });
});
