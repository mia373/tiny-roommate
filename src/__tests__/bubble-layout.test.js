import { describe, it, expect } from 'vitest';
import {
  BUBBLE_LAYOUT_DEFAULTS,
  buildBubbleCandidates,
  expandRect,
  pickBubblePlacement,
  pickBubblePlacementWithinBounds,
  rectOverlapArea,
  resolveBubbleRect,
  resolveBubbleRectWithinBounds,
  resolveWideBubbleSize,
} from '../bubble-layout.js';

describe('buildBubbleCandidates', () => {
  it('only creates upper placements', function() {
    var rect = { left: 100, top: 300, right: 220, bottom: 420, width: 120, height: 120 };
    var candidates = buildBubbleCandidates(rect, 180, 80, 0, 0, BUBBLE_LAYOUT_DEFAULTS.gap);
    expect(candidates.map(function(candidate) { return candidate.name; })).toEqual(['top', 'top-right', 'top-left']);
    expect(candidates.map(function(candidate) { return candidate.arrowSide; })).toEqual(['bottom', 'bottom', 'bottom']);
  });
});

describe('pickBubblePlacement', () => {
  it('keeps the bubble off the pet when there is room above', function() {
    var rect = { left: 500, top: 500, right: 620, bottom: 620, width: 120, height: 120 };
    var placement = pickBubblePlacement(rect, 200, 90, 1440, 900, {
      random: function() { return 0.5; },
    });
    var bubbleRect = resolveBubbleRect(
      placement,
      200,
      90,
      1440,
      900,
      BUBBLE_LAYOUT_DEFAULTS.margin
    );
    var keepOutRect = expandRect(rect, BUBBLE_LAYOUT_DEFAULTS.petPadding);

    expect(['top', 'top-right', 'top-left']).toContain(placement.name);
    expect(rectOverlapArea(bubbleRect, keepOutRect)).toBe(0);
  });

  it('keeps jitter bounded to a small range', function() {
    var rect = { left: 400, top: 520, right: 520, bottom: 640, width: 120, height: 120 };
    var leftBiased = pickBubblePlacement(rect, 180, 88, 1440, 900, {
      random: (function() {
        var values = [0, 0, 0];
        return function() { return values.shift(); };
      })(),
    });
    var rightBiased = pickBubblePlacement(rect, 180, 88, 1440, 900, {
      random: (function() {
        var values = [1, 1, 0];
        return function() { return values.shift(); };
      })(),
    });

    expect(Math.abs(leftBiased.left - rightBiased.left)).toBeLessThanOrEqual(BUBBLE_LAYOUT_DEFAULTS.jitterX);
    expect(Math.abs(leftBiased.top - rightBiased.top)).toBeLessThanOrEqual(BUBBLE_LAYOUT_DEFAULTS.jitterY);
  });

  it('clamps the resolved bubble inside the screen margin', function() {
    var rect = { left: 12, top: 180, right: 132, bottom: 300, width: 120, height: 120 };
    var placement = pickBubblePlacement(rect, 220, 90, 320, 480, {
      random: function() { return 0.5; },
    });
    var bubbleRect = resolveBubbleRect(
      placement,
      220,
      90,
      320,
      480,
      BUBBLE_LAYOUT_DEFAULTS.margin
    );

    expect(bubbleRect.left).toBeGreaterThanOrEqual(BUBBLE_LAYOUT_DEFAULTS.margin);
    expect(bubbleRect.top).toBeGreaterThanOrEqual(BUBBLE_LAYOUT_DEFAULTS.margin);
    expect(bubbleRect.right).toBeLessThanOrEqual(320 - BUBBLE_LAYOUT_DEFAULTS.margin);
  });

  it('keeps the bubble inside negative-coordinate monitor bounds', function() {
    var rect = { left: -1320, top: 320, right: -1200, bottom: 440, width: 120, height: 120 };
    var boundsRect = { left: -1440, top: 0, right: 0, bottom: 900 };
    var placement = pickBubblePlacementWithinBounds(rect, 220, 90, boundsRect, {
      random: function() { return 0.5; },
    });
    var bubbleRect = resolveBubbleRectWithinBounds(
      placement,
      220,
      90,
      boundsRect,
      BUBBLE_LAYOUT_DEFAULTS.margin
    );

    expect(bubbleRect.left).toBeGreaterThanOrEqual(boundsRect.left + BUBBLE_LAYOUT_DEFAULTS.margin);
    expect(bubbleRect.top).toBeGreaterThanOrEqual(boundsRect.top + BUBBLE_LAYOUT_DEFAULTS.margin);
    expect(bubbleRect.right).toBeLessThanOrEqual(boundsRect.right - BUBBLE_LAYOUT_DEFAULTS.margin);
    expect(rectOverlapArea(bubbleRect, expandRect(rect, BUBBLE_LAYOUT_DEFAULTS.petPadding))).toBe(0);
  });
});

describe('resolveWideBubbleSize', () => {
  it('widens tall bubbles until width exceeds height', function() {
    var result = resolveWideBubbleSize(function(width) {
      if (!width) return { width: 140, height: 180 };
      if (width === 180) return { width: 180, height: 160 };
      return { width: width, height: 140 };
    });

    expect(result.width).toBeGreaterThan(result.height);
    expect(result.width).toBeGreaterThanOrEqual(BUBBLE_LAYOUT_DEFAULTS.minWidth);
  });

  it('stops widening at max width', function() {
    var result = resolveWideBubbleSize(function(width) {
      if (!width) return { width: 160, height: 240 };
      return { width: width, height: 320 };
    });

    expect(result.width).toBe(BUBBLE_LAYOUT_DEFAULTS.maxWidth);
  });
});
