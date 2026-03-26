import { describe, it, expect } from 'vitest';
import { CHARACTERS, VOICE, voice } from '../characters.js';

describe('CHARACTERS', () => {
  var characterKeys = Object.keys(CHARACTERS).filter(k => k !== '_default');

  it('every character has defaultName and displayName', () => {
    characterKeys.forEach(key => {
      expect(CHARACTERS[key].defaultName, key + ' missing defaultName').toBeTruthy();
      expect(CHARACTERS[key].displayName, key + ' missing displayName').toBeTruthy();
    });
  });

  it('every character has a matching VOICE entry', () => {
    characterKeys.forEach(key => {
      expect(VOICE[key], key + ' missing from VOICE').toBeDefined();
    });
  });

  it('every VOICE entry has all required fields', () => {
    var required = ['greet', 'acks', 'petHold', 'petLines', 'petFallback', 'tapLines', 'tapFallback', 'chatFallback'];
    Object.keys(VOICE).forEach(key => {
      required.forEach(field => {
        expect(VOICE[key][field], key + ' missing ' + field).toBeDefined();
      });
    });
  });

  it('voice() returns _default for unknown sprite', () => {
    var result = voice({ currentSprite: 'nonexistent_thing' });
    expect(result).toBe(VOICE._default);
  });

  it('voice() returns correct entry for known sprite', () => {
    var result = voice({ currentSprite: 'tabby_cat' });
    expect(result).toBe(VOICE.tabby_cat);
  });

  it('every character has a sprite file referenced', () => {
    // Sprite files should be at public/sprites/{key}.png
    // This test just verifies the naming convention is consistent
    characterKeys.forEach(key => {
      expect(key).toMatch(/^[a-z][a-z0-9_]*$/, key + ' has invalid sprite key format');
    });
  });
});
