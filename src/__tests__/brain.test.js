import { describe, it, expect, vi } from 'vitest';

// Mock Tauri shell plugin before importing brain
vi.mock('@tauri-apps/plugin-shell', () => ({
  Command: { create: () => ({ execute: () => Promise.resolve({ stdout: '', code: 0 }) }) },
}));

const { parseResponse } = await import('../brain.js');

describe('parseResponse', () => {
  it('extracts state and text from JSON + dialogue', () => {
    var raw = '{"state":"happy","r":["💛"]} yay you\'re here!';
    var result = parseResponse(raw);
    expect(result.state).toBe('happy');
    expect(result.reactions).toEqual(['💛']);
    expect(result.text).toContain('yay');
  });

  it('defaults to idle when no JSON found', () => {
    var result = parseResponse('just some text');
    expect(result.state).toBe('idle');
    expect(result.reactions).toEqual([]);
    expect(result.text).toBe('just some text');
  });

  it('strips reasoning lines', () => {
    var raw = "I've read the file.\nLet me think about this.\nhello owner!";
    var result = parseResponse(raw);
    expect(result.text).toBe('hello owner!');
  });

  it('strips markdown code blocks', () => {
    var raw = '```json\n{"foo":"bar"}\n```\nhey there!';
    var result = parseResponse(raw);
    expect(result.text).toContain('hey there');
  });

  it('strips action asterisks', () => {
    var raw = 'hey *looks around* oh nice!';
    var result = parseResponse(raw);
    expect(result.text).not.toContain('*');
    expect(result.text).toContain('oh nice');
  });

  it('truncates long text to first sentence', () => {
    var raw = 'This is a really long sentence that goes on and on and on and on and keeps going forever and ever and ever and more. And then another sentence.';
    var result = parseResponse(raw);
    expect(result.text.length).toBeLessThanOrEqual(150);
  });

  it('handles empty input', () => {
    var result = parseResponse('');
    expect(result.state).toBe('idle');
    expect(result.text).toBe('');
  });

  it('limits reactions to 2', () => {
    var raw = '{"state":"happy","r":["a","b","c","d"]} hi';
    var result = parseResponse(raw);
    expect(result.reactions).toHaveLength(2);
  });
});
