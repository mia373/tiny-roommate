import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const brainMocks = vi.hoisted(function() {
  return {
    think: vi.fn(),
    getActivityLog: vi.fn(),
    generateDailyDigest: vi.fn(),
    loadConfig: vi.fn(),
    saveConfigField: vi.fn(),
    hasCompletedOnboarding: vi.fn(),
    ensurePetDataPath: vi.fn(),
    checkAiCli: vi.fn(),
    getAiProviderInfo: vi.fn(),
    summarizePerceptionsForTimeline: vi.fn(),
  };
});

const signalMocks = vi.hoisted(function() {
  return {
    getTimeSignals: vi.fn(),
    getIdleSeconds: vi.fn(),
    captureScreenContext: vi.fn(),
    buildContextString: vi.fn(),
    isScreenRecordingDenied: vi.fn(),
  };
});

vi.mock('../brain.js', function() {
  return brainMocks;
});

vi.mock('../signals.js', function() {
  return signalMocks;
});

const { initBehavior } = await import('../behavior.js');

function createPet() {
  return {
    canvas: {
      style: {},
      getBoundingClientRect: vi.fn(function() {
        return { left: 0, top: 0, right: 128, bottom: 128 };
      }),
    },
    appWindow: {
      outerPosition: vi.fn().mockResolvedValue({ x: 100, y: 100 }),
      setPosition: vi.fn().mockResolvedValue(undefined),
    },
    sprite: {
      setState: vi.fn(),
      getSize: vi.fn(function() {
        return { width: 128, height: 128 };
      }),
    },
    currentSprite: 'tabby_cat',
    petName: 'Phoebe',
    ownerName: '',
    aiProvider: '',
    isWalking: false,
    llmBusy: false,
    lastInteractionTime: 0,
    mouseNearPet: false,
    isSick: false,
    showBubble: vi.fn(),
    voice: function() {
      return { greet: '👋' };
    },
  };
}

async function flushMicrotasks() {
  for (var i = 0; i < 8; i++) {
    await Promise.resolve();
  }
}

describe('initBehavior onboarding', function() {
  beforeEach(function() {
    vi.useFakeTimers();

    brainMocks.getActivityLog.mockReturnValue([]);
    brainMocks.generateDailyDigest.mockResolvedValue(null);
    brainMocks.think.mockResolvedValue(null);
    brainMocks.saveConfigField.mockResolvedValue(undefined);
    brainMocks.ensurePetDataPath.mockResolvedValue('/tmp/tinyroommate/.pet-data');
    brainMocks.checkAiCli.mockResolvedValue(true);
    brainMocks.getAiProviderInfo.mockReturnValue({
      displayName: 'Claude Code',
      installHint: 'Claude Code (claude.ai/claude-code)',
    });
    brainMocks.summarizePerceptionsForTimeline.mockResolvedValue(null);

    signalMocks.getTimeSignals.mockReturnValue({
      time: '10:00 AM',
      timeOfDay: 'morning',
      dayOfWeek: 'Monday',
      isWeekend: false,
      hour: 10,
    });
    signalMocks.getIdleSeconds.mockReturnValue(0);
    signalMocks.captureScreenContext.mockResolvedValue(null);
    signalMocks.buildContextString.mockReturnValue('Environment');
    signalMocks.isScreenRecordingDenied.mockReturnValue(false);
  });

  afterEach(function() {
    vi.clearAllMocks();
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('runs the first-impression flow only for a new relationship', async function() {
    brainMocks.loadConfig.mockResolvedValue({
      pet: { name: 'Phoebe', born: '2026-03-29T21:00:00.000Z', introducedAt: '' },
      owner: { name: 'Ran' },
      sprite: 'tabby_cat',
      aiProvider: 'claude',
    });
    brainMocks.hasCompletedOnboarding.mockReturnValue(false);
    brainMocks.think.mockResolvedValue({
      text: 'nice desk',
      state: 'happy',
      reactions: ['hi', 'sup'],
    });

    var pet = createPet();
    var behavior = initBehavior(pet);

    behavior.start();
    await vi.advanceTimersByTimeAsync(6000);

    expect(brainMocks.saveConfigField).toHaveBeenCalledWith('introduced_at', expect.any(String));
    expect(brainMocks.think).toHaveBeenCalledTimes(1);
    expect(brainMocks.think.mock.calls[0][0]).toContain('very first time');
    expect(
      pet.showBubble.mock.calls.some(function(call) {
        return String(call[0]).indexOf("hey! i'm Phoebe") !== -1;
      })
    ).toBe(true);
  });

  it('resumes an existing relationship without re-introducing the pet', async function() {
    brainMocks.loadConfig.mockResolvedValue({
      pet: {
        name: 'Phoebe',
        born: '2026-03-29T20:00:00.000Z',
        introducedAt: '2026-03-29T20:05:00.000Z',
      },
      owner: { name: 'Ran' },
      sprite: 'tabby_cat',
      aiProvider: 'claude',
    });
    brainMocks.hasCompletedOnboarding.mockReturnValue(true);

    var pet = createPet();
    var behavior = initBehavior(pet);

    behavior.start();
    await flushMicrotasks();

    expect(brainMocks.saveConfigField).not.toHaveBeenCalled();
    expect(brainMocks.think).not.toHaveBeenCalled();
    expect(signalMocks.captureScreenContext).toHaveBeenCalledTimes(1);
    expect(
      pet.showBubble.mock.calls.some(function(call) {
        return String(call[0]).indexOf("hey! i'm") !== -1;
      })
    ).toBe(false);
  });

  it('backfills the onboarding marker for migrated pet-data without replaying first meeting', async function() {
    brainMocks.loadConfig.mockResolvedValue({
      pet: {
        name: 'Phoebe',
        born: '2026-03-29T20:00:00.000Z',
        introducedAt: '',
      },
      owner: { name: 'Ran' },
      sprite: 'tabby_cat',
      aiProvider: 'claude',
    });
    brainMocks.hasCompletedOnboarding.mockReturnValue(true);

    var pet = createPet();
    var behavior = initBehavior(pet);

    behavior.start();
    await flushMicrotasks();

    expect(brainMocks.saveConfigField).toHaveBeenCalledWith('introduced_at', '2026-03-29T20:00:00.000Z');
    expect(brainMocks.think).not.toHaveBeenCalled();
    expect(
      pet.showBubble.mock.calls.some(function(call) {
        return String(call[0]).indexOf("hey! i'm") !== -1;
      })
    ).toBe(false);
  });
});
