import os
import subprocess
import tkinter as tk
from tkinter import ttk
import pystray
from PIL import Image, ImageDraw

def set_screen_timeout(minutes):
    """Imposta il tempo di sospensione dello schermo (in minuti) tramite powercfg."""
    if minutes == 0:
        # Disattiva lo spegnimento automatico (imposta a 0)
        subprocess.run("powercfg -change -monitor-timeout-ac 0", shell=True)
    else:
        subprocess.run(f"powercfg -change -monitor-timeout-ac {minutes}", shell=True)

def turn_screen_off():
    """Spegne immediatamente lo schermo."""
    # Codice per spegnere lo schermo subito tramite un piccolo script o comando
    subprocess.run("powershell (Add-Type -AssemblyName PresentationCore)$([System.Windows.Input.KeyEventArgs].Assembly.GetType('System.Windows.Input.SafeNativeMethods').GetMethod('SendMessage', [System.Type[]]@([System.IntPtr], [System.Int32], [System.IntPtr], [System.IntPtr])).Invoke($null, @([System.IntPtr]0xFFFF, 0x0112, [System.IntPtr]0xF170, [System.IntPtr]2)))", shell=True)

class ScreenTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Timer Schermo")
        self.root.geometry("220x160")
        self.root.resizable(False, False)
        
        # Rimuovi i bordi standard di Windows per un look più pulito (opzionale)
        # self.root.overrideredirect(True) 

        # Layout principale
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Scritta centrale
        label_title = ttk.Label(main_frame, text="Timer schermo", font=("Segoe UI", 11, "bold"))
        label_title.pack(pady=(0, 10))

        # Menu a tendina per la scelta del tempo (in minuti)
        self.time_var = tk.StringVar(value="10 minuti")
        time_options = ["Mai (0)", "5 minuti", "10 minuti", "15 minuti", "30 minuti", "1 ora"]
        self.dropdown = ttk.Combobox(main_frame, textvariable=self.time_var, values=time_options, state="readonly", width=15)
        self.dropdown.pack(pady=(0, 10))
        self.dropdown.bind("<<ComboboxSelected>>", self.on_time_selected)

        # Pulsanti ON e OFF
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack()

        btn_on = ttk.Button(btn_frame, text="ON", width=8, command=self.turn_on)
        btn_on.pack(side=tk.LEFT, padx=5)

        btn_off = ttk.Button(btn_frame, text="OFF", width=8, command=self.turn_off)
        btn_off.pack(side=tk.RIGHT, padx=5)

        # Gestione chiusura: invece di chiudere, minimizza nella tray di Windows
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        # Creazione dell'icona nella system tray
        self.setup_tray_icon()

    def on_time_selected(self, event):
        val = self.time_var.get()
        if "Mai" in val:
            set_screen_timeout(0)
        elif "ora" in val:
            set_screen_timeout(60)
        else:
            minutes = int(val.split()[0])
            set_screen_timeout(minutes)

    def turn_on(self):
        # Riattiva applicando il valore selezionato nel menu
        self.on_time_selected(None)

    def turn_off(self):
        # Spegne lo schermo immediatamente o disattiva i timer
        turn_screen_off()

    def hide_window(self):
        self.root.withdraw()

    def show_window(self, icon, item):
        self.root.deiconify()

    def quit_app(self, icon, item):
        icon.stop()
        self.root.quit()

    def setup_tray_icon(self):
        # Genera un'icona semplice al volo (un cerchio blu)
        image = Image.new('RGB', (64, 64), color=(30, 30, 30))
        d = ImageDraw.Draw(image)
        d.ellipse([16, 16, 48, 48], fill=(0, 120, 215))

        menu = pystray.Menu(
            pystray.MenuItem('Apri', self.show_window, default=True),
            pystray.MenuItem('Esci', self.quit_app)
        )
        self.tray_icon = pystray.Icon("screen_timer", image, "Timer Schermo", menu)
        
        # Avvia la tray icon in un thread separato per non bloccare Tkinter
        import threading
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenTimerApp(root)
    root.mainloop()