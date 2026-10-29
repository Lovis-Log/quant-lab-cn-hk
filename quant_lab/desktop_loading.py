"""Native first-frame loading surface; imports WinForms only in the desktop UI."""

import threading
import time


class StartupOverlay:
    def __init__(self):
        self.ready = threading.Event()
        self.shown = threading.Event()
        self.panel = None
        self.form = None
        self.view = None
        self.shown_at = None
        self.ready_at = None

    def show(self, window):
        import ctypes
        from System.Drawing import Color, Font, FontStyle, Point, Size
        from System.Windows.Forms import (AutoSizeMode, DockStyle, FlowDirection,
            FlowLayoutPanel, Label, Padding, Panel, ProgressBar, ProgressBarStyle)

        self.form = window.native
        scale = self.form.DeviceDpi / 96.0
        def size(width, height):
            return Size(round(width * scale), round(height * scale))
        panel = Panel()
        panel.BackColor = Color.FromArgb(21, 23, 25)
        panel.Dock = DockStyle.Fill
        content = FlowLayoutPanel()
        content.AutoSize = True
        content.AutoSizeMode = AutoSizeMode.GrowAndShrink
        content.FlowDirection = FlowDirection.TopDown
        content.WrapContents = False
        content.Padding = Padding(round(24 * scale))
        brand = Label()
        brand.Text = "QUANT LAB"
        brand.ForeColor = Color.FromArgb(232, 235, 238)
        brand.Font = Font("Segoe UI", 23, FontStyle.Bold)
        brand.AutoSize = True
        brand.Margin = Padding(0, 0, 0, round(12 * scale))
        status = Label()
        status.Text = "正在准备工作区"
        status.ForeColor = Color.FromArgb(146, 154, 163)
        status.Font = Font("Microsoft YaHei UI", 11)
        status.AutoSize = True
        status.Margin = Padding(0)
        progress = ProgressBar()
        progress.Size = size(360, 5)
        progress.Margin = Padding(0, round(20 * scale), 0, 0)
        progress.Style = ProgressBarStyle.Marquee
        progress.MarqueeAnimationSpeed = 28
        animations = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(animations), 0)
        progress.Visible = bool(animations.value)
        for control in (brand, status, progress):
            content.Controls.Add(control)
        panel.Controls.Add(content)

        def center(*_):
            content.Location = Point(max(0, (panel.Width - content.Width) // 2),
                                     max(0, (panel.Height - content.Height) // 2))
        panel.Resize += center
        content.SizeChanged += center
        self.form.Controls.Add(panel)
        panel.BringToFront()
        center()
        self.panel = panel
        self.shown_at = time.monotonic()
        self.shown.set()
        if self.ready.is_set():
            self._hide()

    def _hide(self):
        if self.form is None or self.panel is None:
            return
        from System import Action

        def remove():
            if self.panel is not None and not self.panel.IsDisposed:
                self.form.Controls.Remove(self.panel)
                self.panel.Dispose()
                self.panel = None
        if self.form.InvokeRequired:
            self.form.BeginInvoke(Action(remove))
        else:
            remove()

    def mark_ready(self, view):
        if view not in ("workspace", "library_setup"):
            return False
        if not self.ready.is_set():
            self.view, self.ready_at = view, time.monotonic()
            self.ready.set()
            self._hide()
        return True


def signal_frontend_ready(view="workspace"):
    """Called only after meaningful app controls have been emitted."""
    import streamlit as st
    st.html(f'''<span class="ql-app-ready" data-view="{view}"></span>
    <script>
    (() => {{
      const signal = () => requestAnimationFrame(() => requestAnimationFrame(() => {{
        const marker = document.querySelector('.ql-app-ready');
        if (marker && !window.__qlFrontendReady && window.pywebview?.api?.frontend_ready) {{
          window.__qlFrontendReady = true;
          window.pywebview.api.frontend_ready(marker.dataset.view);
        }}
      }}));
      signal();
      if (!window.__qlReadyListener) {{
        window.__qlReadyListener = true;
        window.addEventListener('pywebviewready', signal, {{once:true}});
      }}
    }})();
    </script>''', unsafe_allow_javascript=True)
