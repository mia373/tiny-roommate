import { emit, listen } from '@tauri-apps/api/event';
import { getCurrentWindow } from '@tauri-apps/api/window';

const STAGE_PAD = 8;
const HIDE_ANIMATION_MS = 160;

const appWindow = getCurrentWindow();
const bubbleEl = document.getElementById('bubble');
const bubbleTextEl = document.getElementById('bubble-text');
const bubbleArrowEl = document.getElementById('bubble-arrow');
const reactionsEl = document.getElementById('bubble-reactions');
const replyBtn = document.getElementById('bubble-reply');

let hideTimer = null;
let activeId = null;

replyBtn.addEventListener('click', function() {
  emit('bubble:reply', { id: activeId }).catch(function() {});
  hideBubble();
});

function clearArrowStyles() {
  bubbleArrowEl.style.top = '';
  bubbleArrowEl.style.left = '';
  bubbleArrowEl.style.right = '';
  bubbleArrowEl.style.bottom = '';
}

function clearHideTimer() {
  if (hideTimer) {
    clearTimeout(hideTimer);
    hideTimer = null;
  }
}

async function hideBubble(options = {}) {
  clearHideTimer();
  bubbleEl.classList.remove('show');
  await emit('bubble:hidden', { id: activeId });
  if (!options.skipWindowHide) {
    setTimeout(function() {
      appWindow.hide().catch(function() {});
    }, HIDE_ANIMATION_MS);
  }
}

function renderBubble(payload) {
  activeId = payload.id;
  bubbleEl.style.maxWidth = (payload.maxWidth || 280) + 'px';
  bubbleEl.style.width = payload.bubbleWidth ? Math.round(payload.bubbleWidth) + 'px' : 'fit-content';

  // Render quote (user's message) + pet's response
  bubbleTextEl.innerHTML = '';
  if (payload.quote) {
    var quoteEl = document.createElement('div');
    quoteEl.className = 'bubble-quote';
    quoteEl.textContent = payload.quote;
    bubbleTextEl.appendChild(quoteEl);
  }
  bubbleTextEl.appendChild(document.createTextNode(payload.text || ''));

  reactionsEl.innerHTML = '';

  (payload.reactions || []).forEach(function(reaction) {
    const button = document.createElement('button');
    button.textContent = reaction;
    button.addEventListener('click', function() {
      emit('bubble:reaction', { id: activeId, reaction: reaction }).catch(function() {});
      hideBubble();
    });
    reactionsEl.appendChild(button);
  });
}

function applyPlacement(payload) {
  clearArrowStyles();
  bubbleEl.style.left = STAGE_PAD + 'px';
  bubbleEl.style.top = STAGE_PAD + 'px';

  if (payload.arrowSide === 'bottom') {
    bubbleArrowEl.style.bottom = '-5px';
    bubbleArrowEl.style.left = Math.round(payload.arrowOffset - 5) + 'px';
  } else if (payload.arrowSide === 'left') {
    bubbleArrowEl.style.left = '-5px';
    bubbleArrowEl.style.top = Math.round(payload.arrowOffset - 5) + 'px';
  } else {
    bubbleArrowEl.style.right = '-5px';
    bubbleArrowEl.style.top = Math.round(payload.arrowOffset - 5) + 'px';
  }
}

async function applyWindowGeometry(payload) {
  await appWindow.setSize({
    type: payload.sizeType || 'Logical',
    width: payload.windowWidth,
    height: payload.windowHeight,
  });
  await appWindow.setPosition({
    type: payload.positionType || 'Logical',
    x: payload.x,
    y: payload.y,
  });
}

listen('bubble:display', async function(event) {
  clearHideTimer();
  renderBubble(event.payload);
  applyPlacement(event.payload);

  await applyWindowGeometry(event.payload);

  bubbleEl.style.visibility = 'visible';
  await appWindow.show();
  bubbleEl.classList.add('show');

  hideTimer = setTimeout(function() {
    hideBubble();
  }, event.payload.duration || 4000);
});

listen('bubble:hide', function() {
  hideBubble();
});

appWindow.hide().catch(function() {});
emit('bubble:ready', { label: 'bubble' }).catch(function() {});
