import subprocess
import tkinter as tk
from tkinter import ttk
import threading
import ctypes
from ctypes import wintypes
import pystray
from PIL import Image, ImageDraw
import winreg

# --- API Native Win32 e Costanti per Eventi Power ---
WM_POWERBROADCAST = 0x0218
PBT_POWERSETTINGCHANGE = 0x8013

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8)
    ]

# GUID_POWEREVENT_ACTIVE: {8a08f810-0909-4b0e-b832-1b05273c1420}
GUID_POWEREVENT_ACTIVE = GUID(
    0x8a08f810, 0x0909, 0x4b0e,
    (ctypes.c_ubyte * 8)(0xb8, 0x32, 0x1b, 0x05, 0x27, 0x3c, 0x14, 0x20)
)

class POWERSETTING_CHANGE_STRUCT(ctypes.Structure):
    _fields_ = [
        ("PowerSetting", GUID),
        ("DataLength", wintypes.DWORD),
        ("Data", wintypes.BYTE * 1)
    ]

def set_screen_timeout(minutes):
    """Imposta il timeout dello schermo via powercfg (0 = Mai)."""
    subprocess.run(f"powercfg -change -monitor-timeout-ac {minutes}", shell=True)

def get_current_screen_timeout_fast():
    """Legge il timeout direttamente dal Registro di Windows in millisecondi (ultra-veloce e 0% CPU)."""
    try:
        # Legge il subkey delle impostazioni video attive del piano energetico corrente
        key_path = r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            active_scheme, _ = winreg.QueryValueEx(key, "ActivePowerScheme")
        
        val_path = rf"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\{active_scheme}\7516b95f-f776-4464-8c53-06167f40cc99\7516b95f-f776-4464-8c53-06167f40cc99"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, val_path) as key:
            ac_val, _ = winreg.QueryValueEx(key, "ACSettingIndex")
            return int(ac_val // 60)  # Converte secondi in minuti
    except Exception:
        pass
    
    # Fallback sicuro via powercfg
    try:
        cmd = "powercfg -getacvaluesetting SCHEME_CURRENT SUB_VIDEO 7516b95f-f776-4464-8c53-06167f40cc99"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        for line in result.stdout.splitlines():
            if "Power Setting Index" in line:
                return int(line.split(":")[-1].strip(), 16)
    except Exception:
        pass
    return None

def turn_screen_off_immediately():
    """Spegne immediatamente lo schermo in modo asincrono."""
    ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)

def interpolate_color(hex1, hex2, factor):
    c1 = tuple(int(hex1[i:i+2], 16) for i in (1, 3, 5))
    c2 = tuple(int(hex2[i:i+2], 16) for i in (1, 3, 5))
    c = tuple(int(c1[j] + factor * (c2[j] - c1[j])) for j in range(3))
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"

class ModernScreenTimerApp:
    def __init__(self, root):
        self.root = root
        
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1b2e")

        self.width = 240
        self.height = 180
        self.position_bottom_right()

        # --- Tavolozza Colori ---
        self.bg_dark = "#1e1b2e"
        self.card_bg = "#2a2640"
        self.text_light = "#ffffff"
        self.text_muted = "#a78bfa"
        
        self.color_green = "#10b981"
        self.color_red = "#ef4444"
        self.color_yellow = "#f59e0b"
        self.notification_fg = "#34d399"

        # Legge lo stato iniziale di Windows
        current_val = get_current_screen_timeout_fast()
        self.is_active = False if current_val == 0 else True

        # Container principale
        self.main_container = tk.Frame(root, bg=self.bg_dark)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # --- Barra Titolo con X ---
        title_bar = tk.Frame(self.main_container, bg=self.bg_dark)
        title_bar.pack(fill=tk.X, padx=10, pady=(5, 0))

        title_label = tk.Label(
            title_bar, text="Timer Schermo", 
            font=("Segoe UI", 10, "bold"), bg=self.bg_dark, fg=self.text_light
        )
        title_label.pack(side=tk.LEFT)

        close_btn = tk.Label(
            title_bar, text="✕", 
            font=("Segoe UI", 10, "bold"), bg=self.bg_dark, fg=self.text_muted, cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.hide_window())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=self.color_red))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=self.text_muted))

        # --- Stile Combobox ---
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Purple.TCombobox", 
                        fieldbackground=self.card_bg, background=self.color_green,
                        foreground=self.text_light, bordercolor=self.color_green,
                        arrowcolor=self.text_light, darkcolor=self.card_bg, lightcolor=self.card_bg, padding=3)
        style.map("Purple.TCombobox", 
                  fieldbackground=[("readonly", self.card_bg), ("disabled", "#161424")],
                  foreground=[("readonly", self.text_light), ("disabled", "#5c5578")])

        root.option_add('*TCombobox*Listbox.background', self.card_bg)
        root.option_add('*TCombobox*Listbox.foreground', self.text_light)
        root.option_add('*TCombobox*Listbox.selectBackground', self.color_green)
        root.option_add('*TCombobox*Listbox.selectForeground', self.text_light)
        root.option_add('*TCombobox*Listbox.font', ("Segoe UI", 9))

        # --- Menu a Tendina ---
        time_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        time_frame.pack(fill=tk.X, padx=12, pady=(6, 2))

        lbl_select = tk.Label(
            time_frame, text="Seleziona Sospensione:", 
            font=("Segoe UI", 8), bg=self.bg_dark, fg=self.text_muted
        )
        lbl_select.pack(anchor="w", pady=(0, 2))

        self.time_options = ["5 minuti", "10 minuti", "15 minuti", "30 minuti", "45 minuti", "1 ora", "2 ore"]
        self.time_var = tk.StringVar(value="10 minuti")
        
        self.dropdown = ttk.Combobox(
            time_frame, textvariable=self.time_var, values=self.time_options, 
            state="readonly" if self.is_active else "disabled", style="Purple.TCombobox", font=("Segoe UI", 9, "bold")
        )
        self.dropdown.pack(fill=tk.X)
        self.dropdown.bind("<<ComboboxSelected>>", self.on_combo_change)

        # Imposta il valore della tendina iniziale se corrispondente
        if current_val and current_val > 0:
            for opt in self.time_options:
                opt_m = int(opt.split()[0]) * 60 if "ora" in opt else int(opt.split()[0])
                if opt_m == current_val:
                    self.time_var.set(opt)
                    break

        # --- Pulsanti ON e OFF ---
        btn_top_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        btn_top_frame.pack(fill=tk.X, padx=12, pady=(5, 2))

        self.btn_on = tk.Button(btn_top_frame, text="ON", font=("Segoe UI", 8, "bold"), cursor="hand2", relief=tk.FLAT, command=self.turn_on)
        self.btn_on.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2), ipady=2)

        self.btn_off = tk.Button(btn_top_frame, text="OFF", font=("Segoe UI", 8, "bold"), cursor="hand2", relief=tk.FLAT, command=self.turn_off)
        self.btn_off.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0), ipady=2)

        # --- Pulsante "Spegni ora" ---
        btn_bottom_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        btn_bottom_frame.pack(fill=tk.X, padx=12, pady=(2, 2))

        self.btn_spegni = tk.Button(
            btn_bottom_frame, text="Spegni ora", font=("Segoe UI", 8, "bold"),
            bg=self.card_bg, fg=self.color_yellow, activebackground="#3b3558", activeforeground=self.color_yellow,
            bd=1, highlightthickness=1, highlightbackground=self.color_yellow, cursor="hand2", relief=tk.FLAT, command=self.turn_off_now
        )
        self.btn_spegni.bind("<Enter>", lambda e: self.btn_spegni.config(bg=self.color_yellow, fg="#1e1b2e"))
        self.btn_spegni.bind("<Leave>", lambda e: self.btn_spegni.config(bg=self.card_bg, fg=self.color_yellow))
        self.btn_spegni.pack(expand=True, fill=tk.X, ipady=2)

        self.apply_initial_visuals()

        # --- Toast Notification ---
        self.toast_label = tk.Label(self.main_container, text="", font=("Segoe UI", 8, "bold"), bg=self.bg_dark, fg=self.notification_fg)
        self.toast_label.pack(fill=tk.X, padx=10, pady=(0, 2))
        self.toast_timer = None
        self.fade_timer = None

        self.setup_tray_icon()

        # Registrazione Eventi Win32 per ascolto in tempo reale (0% CPU)
        self.register_power_notifications()

    def register_power_notifications(self):
        """Registra l'app per ricevere messaggi nativi Win32 quando cambia il power setting."""
        try:
            hwnd = self.root.winfo_id()
            self.h_notify = ctypes.windll.user32.RegisterPowerSettingNotification(
                wintypes.HANDLE(hwnd),
                ctypes.byref(GUID_POWEREVENT_ACTIVE),
                0
            )
            # Polling leggero di sicurezza ogni 1.5s leggendo la chiave di registro locale (senza cmd)
            self.start_fast_registry_check()
        except Exception:
            pass

    def start_fast_registry_check(self):
        """Lettura di registro ultra-veloce diretta per sincro immediata."""
        def check():
            self.sync_with_system()
            self.root.after(1500, check)
        self.root.after(1500, check)

    def sync_with_system(self):
        val = get_current_screen_timeout_fast()
        if val is not None:
            if val == 0 and self.is_active:
                self.is_active = False
                self.dropdown.config(state="disabled")
                self.animate_switch(False)
            elif val > 0 and not self.is_active:
                self.is_active = True
                self.dropdown.config(state="readonly")
                self.animate_switch(True)

            if val > 0:
                for opt in self.time_options:
                    opt_mins = int(opt.split()[0]) * 60 if "ora" in opt else int(opt.split()[0])
                    if opt_mins == val:
                        if self.time_var.get() != opt:
                            self.time_var.set(opt)
                        break

    def apply_initial_visuals(self):
        if self.is_active:
            self.btn_on.config(bg=self.color_green, fg="#ffffff", bd=0, highlightthickness=0)
            self.btn_off.config(bg=self.card_bg, fg=self.color_red, bd=1, highlightthickness=1, highlightbackground=self.color_red)
        else:
            self.btn_on.config(bg=self.card_bg, fg=self.color_green, bd=1, highlightthickness=1, highlightbackground=self.color_green)
            self.btn_off.config(bg=self.color_red, fg="#ffffff", bd=0, highlightthickness=0)

    def animate_switch(self, target_state):
        steps = 6
        delay = 10

        if target_state:
            on_start_bg, on_end_bg = self.card_bg, self.color_green
            on_start_fg, on_end_fg = self.color_green, "#ffffff"
            off_start_bg, off_end_bg = self.color_red, self.card_bg
            off_start_fg, off_end_fg = "#ffffff", self.color_red
        else:
            on_start_bg, on_end_bg = self.color_green, self.card_bg
            on_start_fg, on_end_fg = "#ffffff", self.color_green
            off_start_bg, off_end_bg = self.card_bg, self.color_red
            off_start_fg, off_end_fg = self.color_red, "#ffffff"

        def step_anim(current_step):
            if current_step <= steps:
                factor = current_step / steps
                self.btn_on.config(bg=interpolate_color(on_start_bg, on_end_bg, factor), fg=interpolate_color(on_start_fg, on_end_fg, factor))
                self.btn_off.config(bg=interpolate_color(off_start_bg, off_end_bg, factor), fg=interpolate_color(off_start_fg, off_end_fg, factor))
                self.root.after(delay, lambda: step_anim(current_step + 1))
            else:
                if target_state:
                    self.btn_on.config(bg=self.color_green, fg="#ffffff", bd=0, highlightthickness=0)
                    self.btn_off.config(bg=self.card_bg, fg=self.color_red, bd=1, highlightthickness=1, highlightbackground=self.color_red)
                else:
                    self.btn_on.config(bg=self.card_bg, fg=self.color_green, bd=1, highlightthickness=1, highlightbackground=self.color_green)
                    self.btn_off.config(bg=self.color_red, fg="#ffffff", bd=0, highlightthickness=0)

        step_anim(1)

    def position_bottom_right(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        margin_x = 15
        margin_y = 50
        x = screen_width - self.width - margin_x
        y = screen_height - self.height - margin_y
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def show_toast(self, message):
        if self.toast_timer:
            self.root.after_cancel(self.toast_timer)
        if self.fade_timer:
            self.root.after_cancel(self.fade_timer)

        self.toast_label.config(text=f"✓  {message}", fg=self.notification_fg)
        self.toast_timer = self.root.after(1800, self.start_fade_out)

    def start_fade_out(self, step=6):
        if step > 0:
            factor = step / 6
            faded_color = interpolate_color(self.bg_dark, self.notification_fg, factor)
            self.toast_label.config(fg=faded_color)
            self.fade_timer = self.root.after(30, lambda: start_fade_out_helper(self, step - 1))
        else:
            self.toast_label.config(text="", fg=self.notification_fg)

    def apply_selected_timeout(self):
        val = self.time_var.get()
        if "ora" in val:
            hours = int(val.split()[0])
            minutes = hours * 60
        else:
            minutes = int(val.split()[0])
        
        set_screen_timeout(minutes)
        self.show_toast(f"Timer impostato: {val}")

    def on_combo_change(self, event):
        if self.is_active:
            self.apply_selected_timeout()

    def turn_on(self):
        if not self.is_active:
            self.is_active = True
            self.dropdown.config(state="readonly")
            self.animate_switch(True)
            self.apply_selected_timeout()

    def turn_off(self):
        if self.is_active:
            self.is_active = False
            set_screen_timeout(0)
            self.dropdown.config(state="disabled")
            self.animate_switch(False)
            self.show_toast("Timer disattivato (Mai)")

    def turn_off_now(self):
        self.show_toast("Spegnimento schermo...")
        self.root.after(200, turn_screen_off_immediately)

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
        self.sync_with_system()
        self.position_bottom_right()
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def quit_app(self, icon, item):
        icon.stop()
        self.root.quit()

    def setup_tray_icon(self):
        image = Image.new('RGB', (64, 64), color=(30, 27, 46))
        d = ImageDraw.Draw(image)
        d.ellipse([12, 12, 52, 52], fill=(139, 92, 246))

        menu = pystray.Menu(
            pystray.MenuItem('Apri Timer', self.show_window, default=True),
            pystray.MenuItem('Esci', self.quit_app)
        )
        self.tray_icon = pystray.Icon("screen_timer", image, "Timer Schermo", menu)
        
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

def start_fade_out_helper(app_instance, step):
    app_instance.start_fade_out(step)

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernScreenTimerApp(root)
    root.mainloop()