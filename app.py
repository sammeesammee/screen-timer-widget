import subprocess
import tkinter as tk
from tkinter import ttk
import threading
import pystray
from PIL import Image, ImageDraw

def set_screen_timeout(minutes):
    """Imposta il timeout dello schermo su Windows via powercfg (0 = Mai)."""
    subprocess.run(f"powercfg -change -monitor-timeout-ac {minutes}", shell=True)

class ModernScreenTimerApp:
    def __init__(self, root):
        self.root = root
        
        # Configurazioni finestra principale
        self.root.overrideredirect(True)  # Rimuove i bordi standard di Windows
        self.root.attributes("-topmost", True)  # La mantiene sempre sopra
        self.root.configure(bg="#1e1b2e")  # Sfondo viola scuro

        # Dimensioni della finestra
        self.width = 240
        self.height = 210
        
        # Posiziona la finestra in basso a destra (sopra le icone della tray area)
        self.position_bottom_right()

        # --- Tavolozza Colori Viola ---
        BG_DARK = "#1e1b2e"
        CARD_BG = "#2a2640"
        TEXT_LIGHT = "#ffffff"
        TEXT_MUTED = "#a78bfa"
        ACCENT_PURPLE = "#8b5cf6"
        ACCENT_HOVER = "#7c3aed"
        CLOSE_HOVER = "#ef4444"
        NOTIFICATION_FG = "#34d399"  # Verde smeraldo per il toast

        # Bordo esterno decorativo viola
        self.border_frame = tk.Frame(root, bg=ACCENT_PURPLE, bd=1)
        self.border_frame.pack(fill=tk.BOTH, expand=True)

        self.main_container = tk.Frame(self.border_frame, bg=BG_DARK)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # --- Barra Titolo Personalizzata con Pulsante X ---
        title_bar = tk.Frame(self.main_container, bg=BG_DARK)
        title_bar.pack(fill=tk.X, padx=10, pady=(8, 0))

        title_label = tk.Label(
            title_bar, 
            text="Timer Schermo", 
            font=("Segoe UI", 10, "bold"), 
            bg=BG_DARK, 
            fg=TEXT_LIGHT
        )
        title_label.pack(side=tk.LEFT)

        close_btn = tk.Label(
            title_bar, 
            text="✕", 
            font=("Segoe UI", 10, "bold"), 
            bg=BG_DARK, 
            fg=TEXT_MUTED, 
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.hide_window())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=CLOSE_HOVER))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=TEXT_MUTED))

        # --- Stile Personalizzato per Combobox Tkinter ---
        style = ttk.Style()
        style.theme_use('default')
        
        style.configure("Purple.TCombobox", 
                        fieldbackground=CARD_BG,
                        background=ACCENT_PURPLE,
                        foreground=TEXT_LIGHT,
                        bordercolor=ACCENT_PURPLE,
                        arrowcolor=TEXT_LIGHT,
                        darkcolor=CARD_BG,
                        lightcolor=CARD_BG,
                        padding=4)
        
        style.map("Purple.TCombobox", 
                  fieldbackground=[("readonly", CARD_BG), ("disabled", "#161424")],
                  foreground=[("readonly", TEXT_LIGHT), ("disabled", "#5c5578")],
                  selectbackground=[("readonly", CARD_BG)],
                  selectforeground=[("readonly", TEXT_LIGHT)])

        root.option_add('*TCombobox*Listbox.background', CARD_BG)
        root.option_add('*TCombobox*Listbox.foreground', TEXT_LIGHT)
        root.option_add('*TCombobox*Listbox.selectBackground', ACCENT_PURPLE)
        root.option_add('*TCombobox*Listbox.selectForeground', TEXT_LIGHT)
        root.option_add('*TCombobox*Listbox.font', ("Segoe UI", 9))

        # --- Menu a Tendina ---
        time_frame = tk.Frame(self.main_container, bg=BG_DARK)
        time_frame.pack(fill=tk.X, padx=15, pady=(12, 5))

        lbl_select = tk.Label(
            time_frame, 
            text="Seleziona Sospensione:", 
            font=("Segoe UI", 8), 
            bg=BG_DARK, 
            fg=TEXT_MUTED
        )
        lbl_select.pack(anchor="w", pady=(0, 3))

        self.time_options = [
            "5 minuti", 
            "10 minuti", 
            "15 minuti", 
            "30 minuti", 
            "45 minuti", 
            "1 ora", 
            "2 ore"
        ]
        self.time_var = tk.StringVar(value="10 minuti")
        
        self.dropdown = ttk.Combobox(
            time_frame, 
            textvariable=self.time_var, 
            values=self.time_options, 
            state="readonly",
            style="Purple.TCombobox",
            font=("Segoe UI", 9, "bold")
        )
        self.dropdown.pack(fill=tk.X)
        self.dropdown.bind("<<ComboboxSelected>>", self.on_combo_change)

        # --- Pulsanti ON e OFF ---
        btn_frame = tk.Frame(self.main_container, bg=BG_DARK)
        btn_frame.pack(fill=tk.X, padx=15, pady=(8, 5))

        self.btn_on = tk.Button(
            btn_frame, 
            text="ON", 
            font=("Segoe UI", 9, "bold"),
            bg=ACCENT_PURPLE, 
            fg=TEXT_LIGHT, 
            activebackground=ACCENT_HOVER, 
            activeforeground=TEXT_LIGHT,
            bd=0, 
            cursor="hand2",
            relief=tk.FLAT,
            command=self.turn_on
        )
        self.btn_on.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4), ipady=3)

        self.btn_off = tk.Button(
            btn_frame, 
            text="OFF", 
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG, 
            fg=TEXT_LIGHT, 
            activebackground="#3b3558", 
            activeforeground=TEXT_LIGHT,
            bd=0, 
            cursor="hand2",
            relief=tk.FLAT,
            command=self.turn_off
        )
        self.btn_off.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(4, 0), ipady=3)

        # Effetti Hover
        self.btn_on.bind("<Enter>", lambda e: self.btn_on.config(bg=ACCENT_HOVER))
        self.btn_on.bind("<Leave>", lambda e: self.btn_on.config(bg=ACCENT_PURPLE))
        self.btn_off.bind("<Enter>", lambda e: self.btn_off.config(bg="#3b3558"))
        self.btn_off.bind("<Leave>", lambda e: self.btn_off.config(bg=CARD_BG))

        # --- Toast Notification ---
        self.toast_label = tk.Label(
            self.main_container,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=BG_DARK,
            fg=NOTIFICATION_FG
        )
        self.toast_label.pack(fill=tk.X, padx=10, pady=(2, 6))
        self.toast_timer = None

        self.setup_tray_icon()

    def position_bottom_right(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        margin_x = 15
        margin_y = 50
        x = screen_width - self.width - margin_x
        y = screen_height - self.height - margin_y
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def show_toast(self, message):
        self.toast_label.config(text=f"✓  {message}")
        if self.toast_timer:
            self.root.after_cancel(self.toast_timer)
        self.toast_timer = self.root.after(2500, lambda: self.toast_label.config(text=""))

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
        self.apply_selected_timeout()

    def turn_on(self):
        # Riattiva la tendina e applica il timer scelto
        self.dropdown.config(state="readonly")
        self.apply_selected_timeout()

    def turn_off(self):
        # Disattiva il timer impostandolo a 0 (Mai) e blocca la tendina
        set_screen_timeout(0)
        self.dropdown.config(state="disabled")
        self.show_toast("Timer disattivato (Mai)")

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon=None, item=None):
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

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernScreenTimerApp(root)
    root.mainloop()