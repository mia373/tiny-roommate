import { lstat, readFile, readlink } from 'node:fs/promises';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Tauri shell plugin before importing brain
var createMock = vi.fn();
vi.mock('@tauri-apps/plugin-shell', () => ({
  Command: { create: createMock },
}));

createMock.mockImplementation(function() {
  return {
    execute: function() {
      return Promise.resolve({ stdout: '', stderr: '', code: 0 });
    },
  };
});

const {
  getConfig,
  getSupportedAiProviders,
  hasCompletedOnboarding,
  normalizeAiProvider,
  parseResponse,
  saveConfigField,
  saveConfigFields,
  think,
} = await import('../brain.js');

beforeEach(function() {
  createMock.mockClear();
  createMock.mockImplementation(function(command, args) {
    return {
      execute: function() {
        if (command === 'bash') {
          var script = Array.isArray(args) ? args[1] : '';
          if (script && script.indexOf('while [ ! -f "$dir/package.json" ]') >= 0) {
            return Promise.resolve({ stdout: '/tmp/tinyroommate-pr7-followup\n', stderr: '', code: 0 });
          }
          return Promise.resolve({ stdout: '', stderr: '', code: 0 });
        }
        return Promise.resolve({ stdout: '', stderr: '', code: 0 });
      },
    };
  });
});

describe('parseResponse', () => {
  it('extracts text, state, reactions from clean JSON', () => {
    var result = parseResponse('{"text":"嗨 Boss!","state":"happy","r":["👋","😊"]}');
    expect(result.text).toBe('嗨 Boss!');
    expect(result.state).toBe('happy');
    expect(result.reactions).toEqual(['👋', '😊']);
  });

  it('handles quiet response (no text)', () => {
    var result = parseResponse('{"state":"idle"}');
    expect(result.text).toBe('');
    expect(result.state).toBe('idle');
  });

  it('ignores reasoning leaked before JSON', () => {
    var raw = '根据配置，我应该用中文回应。这是一个互动时刻。\n{"text":"嗨 Boss! 在呢!","state":"happy"}';
    var result = parseResponse(raw);
    expect(result.text).toBe('嗨 Boss! 在呢!');
    expect(result.text).not.toContain('根据');
  });

  it('ignores English reasoning leaked before JSON', () => {
    var raw = 'I should respond playfully here. Let me think about what to say.\n{"text":"Hey! What\'s up?","state":"happy"}';
    var result = parseResponse(raw);
    expect(result.text).toBe("Hey! What's up?");
    expect(result.text).not.toContain('should');
  });

  it('strips markdown from text field', () => {
    var result = parseResponse('{"text":"**they are in flow**","state":"idle"}');
    expect(result.text).toBe('they are in flow');
  });

  it('defaults to idle when no JSON found', () => {
    var result = parseResponse('just some random text');
    expect(result.state).toBe('idle');
    expect(result.text).toBe('');
  });

  it('handles empty input', () => {
    var result = parseResponse('');
    expect(result.state).toBe('idle');
    expect(result.text).toBe('');
  });

  it('limits reactions to 2', () => {
    var result = parseResponse('{"state":"happy","text":"hi","r":["a","b","c","d"]}');
    expect(result.reactions).toHaveLength(2);
  });

  it('picks last valid JSON when multiple present', () => {
    var raw = '{"foo":"bar"}\nsome reasoning\n{"text":"yo!","state":"walk"}';
    var result = parseResponse(raw);
    expect(result.text).toBe('yo!');
    expect(result.state).toBe('walk');
  });

  it('truncates long text to first sentence', () => {
    var result = parseResponse('{"text":"This is a really long sentence that goes on and on and on and on and keeps going forever and ever more. And another.","state":"idle"}');
    expect(result.text.length).toBeLessThanOrEqual(120);
  });
});

describe('saveConfigFields', () => {
  it('updates multiple config fields together in memory', async function() {
    await saveConfigFields({
      pet_name: 'Mochi',
      owner_name: 'Ran',
      sprite: 'tuxedo_cat',
      pet_scale: '1.8',
      ai_provider: 'gemini',
      introduced_at: '2026-03-29T15:20:00.000Z',
    });

    var config = getConfig();
    expect(config.pet.name).toBe('Mochi');
    expect(config.owner.name).toBe('Ran');
    expect(config.sprite).toBe('tuxedo_cat');
    expect(config.pet_scale).toBe(1.8);
    expect(config.aiProvider).toBe('gemini');
    expect(config.pet.introducedAt).toBe('2026-03-29T15:20:00.000Z');
  });
});

describe('AI provider helpers', () => {
  it('normalizes supported providers and rejects unknown values', () => {
    expect(normalizeAiProvider('Claude')).toBe('claude');
    expect(normalizeAiProvider(' gemini ')).toBe('gemini');
    expect(normalizeAiProvider('openai')).toBe('');
    expect(normalizeAiProvider('')).toBe('');
  });

  it('exposes both supported AI providers', () => {
    var providers = getSupportedAiProviders().map(function(provider) { return provider.id; });
    expect(providers).toContain('claude');
    expect(providers).toContain('gemini');
  });

  it('uses the newly selected provider without requiring a restart', async () => {
    await saveConfigField('ai_provider', 'gemini');

    createMock.mockImplementation(function(command, args) {
      return {
        execute: function() {
          if (command === 'bash') {
            var script = Array.isArray(args) ? args[1] : '';
            if (script && script.indexOf('while [ ! -f "$dir/package.json" ]') >= 0) {
              return Promise.resolve({ stdout: '/tmp/tinyroommate-pr7-followup\n', stderr: '', code: 0 });
            }
            return Promise.resolve({ stdout: '', stderr: '', code: 0 });
          }
          if (command === 'gemini' && Array.isArray(args) && args[0] === '--version') {
            return Promise.resolve({ stdout: '1.0.0\n', stderr: '', code: 0 });
          }
          if (command === 'gemini' && Array.isArray(args) && args[0] === '-p') {
            return Promise.resolve({ stdout: '{"text":"hi from gemini","state":"happy"}', stderr: '', code: 0 });
          }
          throw new Error('Unexpected command: ' + command + ' ' + JSON.stringify(args || []));
        },
      };
    });

    var result = await think('say hi');

    expect(result).toEqual({
      text: 'hi from gemini',
      state: 'happy',
      reactions: [],
    });
    expect(createMock).toHaveBeenCalledWith('gemini', ['--version']);
    expect(
      createMock.mock.calls.some(function(call) {
        return call[0] === 'gemini' && Array.isArray(call[1]) && call[1][0] === '-p';
      })
    ).toBe(true);
  });
});

describe('hasCompletedOnboarding', () => {
  it('returns false for a freshly created pet-data relationship without onboarding marker', function() {
    expect(hasCompletedOnboarding({
      pet: {
        introducedAt: '',
        born: new Date(Date.now() - 60 * 1000).toISOString(),
      },
    })).toBe(false);
  });

  it('returns true when onboarding marker exists', function() {
    expect(hasCompletedOnboarding({ pet: { introducedAt: '2026-03-29T15:20:00.000Z' } })).toBe(true);
  });

  it('treats older pet-data as an existing relationship during migration', function() {
    expect(hasCompletedOnboarding({
      pet: {
        introducedAt: '',
        born: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      },
    })).toBe(true);
  });
});

describe('template config defaults', () => {
  it('does not hard-code a default pet scale in the template', async () => {
    var text = await readFile(process.cwd() + '/.pet-data-template/config.md', 'utf8');
    expect(text).not.toContain('pet_scale: 1.5');
  });
});

describe('pet prompt template files', () => {
  it('keeps CLAUDE.md and GEMINI.md as symlinks to AGENTS.md', async () => {
    var claudePath = process.cwd() + '/.pet-data-template/CLAUDE.md';
    var geminiPath = process.cwd() + '/.pet-data-template/GEMINI.md';

    expect((await lstat(claudePath)).isSymbolicLink()).toBe(true);
    expect((await lstat(geminiPath)).isSymbolicLink()).toBe(true);
    expect(await readlink(claudePath)).toBe('AGENTS.md');
    expect(await readlink(geminiPath)).toBe('AGENTS.md');
  });
});
