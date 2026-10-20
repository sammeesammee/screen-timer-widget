import subprocess
import tkinter as tk
from tkinter import ttk
import threading
import ctypes
import pystray
from PIL import Image, ImageDraw

def set_screen_timeout(minutes):
    """Imposta il timeout dello schermo su Windows via powercfg (0 = Mai)."""
    subprocess.run(f"powercfg -change -monitor-timeout-ac {minutes}", shell=True)

def turn_screen_off_immediately():
    """Spegne immediatamente lo schermo in modo asincrono (evita il blocco di Tkinter)."""
    # PostMessageW non blocca il thread principale dell'applicazione
    ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)

class ModernScreenTimerApp:
    def __init__(self, root):
        self.root = root
        
        # Configurazioni finestra principale
        self.root.overrideredirect(True)  # Rimuove i bordi standard di Windows
        self.root.attributes("-topmost", True)  # La mantiene sempre sopra
        self.root.configure(bg="#1e1b2e")  # Sfondo viola scuro

        # Dimensioni della finestra
        self.width = 240
        self.height = 230
        
        # Posiziona la finestra in basso a destra sopra la taskbar
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

        # Stato iniziale: Timer attivo su 10 minuti
        self.is_active = True

        # Bordo esterno decorativo viola
        self.border_frame = tk.Frame(root, bg=self.color_green, bd=1)
        self.border_frame.pack(fill=tk.BOTH, expand=True)

        self.main_container = tk.Frame(self.border_frame, bg=self.bg_dark)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # --- Barra Titolo Personalizzata con Pulsante X ---
        title_bar = tk.Frame(self.main_container, bg=self.bg_dark)
        title_bar.pack(fill=tk.X, padx=10, pady=(8, 0))

        title_label = tk.Label(
            title_bar, 
            text="Timer Schermo", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.bg_dark, 
            fg=self.text_light
        )
        title_label.pack(side=tk.LEFT)

        close_btn = tk.Label(
            title_bar, 
            text="✕", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.bg_dark, 
            fg=self.text_muted, 
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.hide_window())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=self.color_red))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=self.text_muted))

        # --- Stile Personalizzato per Combobox Tkinter ---
        style = ttk.Style()
        style.theme_use('default')
        
        style.configure("Purple.TCombobox", 
                        fieldbackground=self.card_bg,
                        background=self.color_green,
                        foreground=self.text_light,
                        bordercolor=self.color_green,
                        arrowcolor=self.text_light,
                        darkcolor=self.card_bg,
                        lightcolor=self.card_bg,
                        padding=4)
        
        style.map("Purple.TCombobox", 
                  fieldbackground=[("readonly", self.card_bg), ("disabled", "#161424")],
                  foreground=[("readonly", self.text_light), ("disabled", "#5c5578")],
                  selectbackground=[("readonly", self.card_bg)],
                  selectforeground=[("readonly", self.text_light)])

        root.option_add('*TCombobox*Listbox.background', self.card_bg)
        root.option_add('*TCombobox*Listbox.foreground', self.text_light)
        root.option_add('*TCombobox*Listbox.selectBackground', self.color_green)
        root.option_add('*TCombobox*Listbox.selectForeground', self.text_light)
        root.option_add('*TCombobox*Listbox.font', ("Segoe UI", 9))

        # --- Menu a Tendina ---
        time_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        time_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        lbl_select = tk.Label(
            time_frame, 
            text="Seleziona Sospensione:", 
            font=("Segoe UI", 8), 
            bg=self.bg_dark, 
            fg=self.text_muted
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

        # --- Pulsanti ON e OFF (Prima Riga) ---
        btn_top_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        btn_top_frame.pack(fill=tk.X, padx=15, pady=(8, 4))

        self.btn_on = tk.Button(
            btn_top_frame, 
            text="ON", 
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            command=self.turn_on
        )
        self.btn_on.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3), ipady=3)

        self.btn_off = tk.Button(
            btn_top_frame, 
            text="OFF", 
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            command=self.turn_off
        )
        self.btn_off.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(3, 0), ipady=3)

        # --- Pulsante "Spegni ora" (Seconda Riga, Centrale) ---
        btn_bottom_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        btn_bottom_frame.pack(fill=tk.X, padx=15, pady=(2, 4))

        self.btn_spegni = tk.Button(
            btn_bottom_frame, 
            text="Spegni ora", 
            font=("Segoe UI", 8, "bold"),
            bg=self.card_bg,
            fg=self.color_yellow,
            activebackground="#3b3558",
            activeforeground=self.color_yellow,
            bd=1,
            highlightthickness=1,
            highlightbackground=self.color_yellow,
            cursor="hand2",
            relief=tk.FLAT,
            command=self.turn_off_now
        )
        self.btn_spegni.bind("<Enter>", lambda e: self.btn_spegni.config(bg=self.color_yellow, fg="#1e1b2e"))
        self.btn_spegni.bind("<Leave>", lambda e: self.btn_spegni.config(bg=self.card_bg, fg=self.color_yellow))
        
        self.btn_spegni.pack(expand=True, fill=tk.X, ipady=3)

        # Aggiorna lo stato visivo iniziale dei bottoni ON/OFF
        self.update_button_visuals()

        # --- Toast Notification ---
        self.toast_label = tk.Label(
            self.main_container,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg=self.bg_dark,
            fg=self.notification_fg
        )
        self.toast_label.pack(fill=tk.X, padx=10, pady=(2, 6))
        self.toast_timer = None

        self.setup_tray_icon()

    def update_button_visuals(self):
        if self.is_active:
            self.btn_on.config(
                bg=self.color_green, fg="#ffffff", 
                activebackground="#059669", activeforeground="#ffffff", bd=0,
                highlightthickness=0
            )
            self.btn_off.config(
                bg=self.card_bg, fg=self.color_red, 
                activebackground="#3b3558", activeforeground=self.color_red, 
                bd=1, highlightthickness=1, highlightbackground=self.color_red
            )
        else:
            self.btn_on.config(
                bg=self.card_bg, fg=self.color_green, 
                activebackground="#3b3558", activeforeground=self.color_green, 
                bd=1, highlightthickness=1, highlightbackground=self.color_green
            )
            self.btn_off.config(
                bg=self.color_red, fg="#ffffff", 
                activebackground="#dc2626", activeforeground="#ffffff", bd=0,
                highlightthickness=0
            )

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
        if self.is_active:
            self.apply_selected_timeout()

    def turn_on(self):
        self.is_active = True
        self.dropdown.config(state="readonly")
        self.update_button_visuals()
        self.apply_selected_timeout()

    def turn_off(self):
        self.is_active = False
        set_screen_timeout(0)  # Imposta su Mai
        self.dropdown.config(state="disabled")
        self.update_button_visuals()
        self.show_toast("Timer disattivato (Mai)")

    def turn_off_now(self):
        self.show_toast("Spegnimento schermo in corso...")
        # Esegue in modo asincrono immediato senza bloccare il thread di Tkinter
        self.root.after(200, turn_screen_off_immediately)

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