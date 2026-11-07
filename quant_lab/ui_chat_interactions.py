"""DOM-only assistant input and reading behaviour; never initiates API calls."""

COMPOSER_JS = """
<script>(() => {
  window.__quantLabComposerCleanup?.();
  let controller, currentArea, currentSend, frame = 0;
  const bind = () => {
    const area = document.querySelector('.st-key-deepseek_composer textarea');
    const send = document.querySelector('.st-key-deepseek_send button');
    if (!area || !send || (area === currentArea && send === currentSend)) return;
    controller?.abort();
    controller = new AbortController();
    const options = {signal:controller.signal};
    currentArea = area; currentSend = send;
    area.dataset.enterSendBound = '1';
    let composing = false, confirming = false, locked = false, scheduled = false;
    const grow = () => {
      area.style.height = 'auto';
      area.style.height = `${Math.min(240, Math.max(92, area.scrollHeight))}px`;
      area.style.overflowY = area.scrollHeight > 240 ? 'auto' : 'hidden';
    };
    area.addEventListener('input', () => { grow(); requestAnimationFrame(grow); }, options);
    area.addEventListener('compositionstart', () => { composing = true; confirming = false; }, options);
    area.addEventListener('compositionend', () => {
      composing = false;
      // Only guard the companion event in this browser event turn, not a time window.
      confirming = true;
      setTimeout(() => { confirming = false; }, 0);
      grow();
    }, options);
    area.addEventListener('keydown', event => {
      if (event.key !== 'Enter' || event.shiftKey) return;
      if (composing || confirming || event.isComposing || event.keyCode === 229) return;
      event.preventDefault();
      if (event.repeat || locked || scheduled || send.disabled || !area.value.trim()) return;
      scheduled = true;
      const value = area.value;
      area.blur();
      setTimeout(() => {
        scheduled = false;
        const current = document.querySelector('.st-key-deepseek_composer textarea');
        const button = document.querySelector('.st-key-deepseek_send button');
        if (current === area && button === send && area.isConnected && area.value === value && !send.disabled) send.click();
      }, 250);
    }, options);
    send.addEventListener('click', event => {
      if (locked || composing || confirming) {
        event.preventDefault(); event.stopImmediatePropagation(); return;
      }
      if (area.value.trim() && !send.disabled) locked = true;
    }, {capture:true, signal:controller.signal});
    grow(); requestAnimationFrame(grow);
  };
  const schedule = () => {
    if (!frame) frame = requestAnimationFrame(() => { frame=0; bind(); });
  };
  const observer = new MutationObserver(schedule);
  const root = document.querySelector('.st-key-deepseek_side_panel');
  if (root) observer.observe(root, {childList:true, subtree:true});
  window.__quantLabComposerCleanup = () => {
    observer.disconnect(); controller?.abort(); if (frame) cancelAnimationFrame(frame);
  };
  bind(); schedule();
})();</script>
"""

MESSAGES_JS = """
<script>(() => {
  const panel = document.querySelector('.st-key-deepseek_messages');
  const marker = document.querySelector('.ql-chat-scroll-scope');
  if (!panel || !marker) return;
  const scope = marker.dataset.scope;
  const states = window.__quantLabChatScrollStates ||= new Map();
  if (!states.has(scope)) {
    if (states.size >= 32) states.delete(states.keys().next().value);
    states.set(scope, {follow:true, top:0});
  }
  const state = states.get(scope);
  window.__quantLabChatScrollCleanup?.();
  let frame = 0;
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'ql-chat-latest';
  button.textContent = '回到最新回复 ↓'; button.setAttribute('aria-label', '回到最新回复');
  panel.parentElement.appendChild(button);
  const nearBottom = () => panel.scrollHeight - panel.scrollTop - panel.clientHeight <= 80;
  const update = () => { button.hidden = state.follow || nearBottom(); };
  const scroll = () => { state.follow = nearBottom(); state.top = panel.scrollTop; update(); };
  const schedule = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      if (state.follow) panel.scrollTop = panel.scrollHeight;
      else panel.scrollTop = state.top;
      update();
    });
  };
  button.addEventListener('click', () => { state.follow = true; schedule(); });
  panel.addEventListener('scroll', scroll, {passive:true});
  const observer = new MutationObserver(schedule);
  observer.observe(panel, {childList:true, subtree:true, characterData:true});
  const resize = new ResizeObserver(schedule);
  resize.observe(panel);
  // Observe content height changes too (code blocks, images, streamed text).
  for (const child of panel.children) resize.observe(child);
  const lifecycle = new MutationObserver(() => { if (!panel.isConnected) cleanup(); });
  lifecycle.observe(document.body, {childList:true, subtree:true});
  const cleanup = () => {
    observer.disconnect(); resize.disconnect(); lifecycle.disconnect();
    panel.removeEventListener('scroll', scroll);
    if (frame) cancelAnimationFrame(frame);
    button.remove();
  };
  window.__quantLabChatScrollCleanup = cleanup;
  schedule();
})();</script>
"""
