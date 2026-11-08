"""Chart gestures and panel exits without cloning Streamlit controls."""

CHART_INTERACTIONS_JS = """
<script>
(() => {
  // Replacing this listener on redraw also releases the previous closure.
  if (window.__quantLabChartWheel) {
    document.removeEventListener('wheel', window.__quantLabChartWheel, true);
  }
  window.__quantLabChartWheel = event => {
    const chart = event.target.closest?.('[data-testid="stPlotlyChart"]');
    if (!chart) return;
    if (event.ctrlKey) {
      // Prevent WebView/browser page zoom while allowing Plotly's native handler.
      event.preventDefault();
    } else {
      // Keep native page scrolling; do not pass ordinary wheels to Plotly.
      event.stopPropagation();
    }
  };
  document.addEventListener('wheel', window.__quantLabChartWheel, {capture:true, passive:false});

  // Play the exit before Streamlit removes the live controls. Never clone forms.
  if (window.__quantLabPanelExit) document.removeEventListener('click', window.__quantLabPanelExit, true);
  window.__quantLabPanelExit = event => {
    if (event.defaultPrevented || event.button !== 0) return;
    const button = event.target.closest?.('button');
    if (!button || button.dataset.qlClosing === 'dispatch') return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches ||
      document.documentElement.dataset.reduceMotion === 'true';
    if (reduced) return;
    let panel;
    for (const kind of ['manual','deepseek','notes','settings']) {
      const trigger = button.closest(kind === 'settings' ? '.st-key-settings_close,.st-key-settings_toggle' :
        `.st-key-${kind}_panel_close,.st-key-${kind}_panel_toggle`);
      if (trigger) {
        panel = [...document.querySelectorAll(kind === 'settings' ? '.st-key-settings_panel' : `.st-key-${kind}_side_panel`)].at(-1);
        break;
      }
    }
    if (!panel || getComputedStyle(panel).display === 'none' || panel.inert) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (panel.dataset.qlClosing) return;
    panel.dataset.qlClosing = 'animating';
    const animation = panel.animate([
      {opacity:1, transform:'translateX(0)'},
      {opacity:0, transform:'translateX(18px)'}
    ], {duration:150, easing:'cubic-bezier(.4,0,1,1)', fill:'forwards'});
    animation.finished.catch(() => {}).then(() => {
      if (button.isConnected) {
        button.dataset.qlClosing = 'dispatch';
        button.click();
        delete button.dataset.qlClosing;
      } else {
        animation.cancel();
      }
    });
  };
  document.addEventListener('click', window.__quantLabPanelExit, true);
})();
</script>
"""
