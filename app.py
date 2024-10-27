import logging
from logging.handlers import TimedRotatingFileHandler

# Inizializza il logger globale
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Livello di default

# Formattazione dei log
log_format = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler con rotazione
file_handler = TimedRotatingFileHandler(
    'app.log',
    when='midnight',
    interval=1,
    backupCount=7,
    encoding='utf-8'
)
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)


import ttkbootstrap as ttk
from tkinter.constants import *
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Querybox
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.widgets import Progressbar
from tkinter import filedialog
import subprocess
from aws_manager import AWSManager
import threading
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import random
import psutil
import win32process
import win32con
import win32gui
import time
import socket
import tkinter as tk
import os
import sys
import webbrowser
from tkinter import Menu

from PIL import Image, ImageTk  # Assicurati di avere Pillow installato per ridimensionare le immagini

# def setup_logging(log_level):
#     logger = logging.getLogger()
#     logger.setLevel(log_level)

#     # File handler
#     file_handler = TimedRotatingFileHandler('app.log', when='midnight', interval=1, backupCount=3)
#     file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     file_handler.setFormatter(file_formatter)
#     logger.addHandler(file_handler)

#     # Console handler
#     console_handler = logging.StreamHandler()
#     console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     console_handler.setFormatter(console_formatter)
#     logger.addHandler(console_handler)

#     return logger

# # Load preferences and set up logging
# try:
#     with open('preferences.json', 'r') as f:
#         preferences = json.load(f)
#     log_level = preferences.get('log_level', 'DEBUG')
# except FileNotFoundError:
#     log_level = 'DEBUG'
#     preferences = {}

# log_level = getattr(logging, log_level)
# logger = setup_logging(log_level)


def setup_logging(log_level):
    """Aggiorna il livello del logger esistente."""
    global logger
    logger.setLevel(log_level)
    
    # Aggiorna il livello per tutti gli handler
    for handler in logger.handlers:
        handler.setLevel(log_level)
    
    return logger



class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Loading...")
        self.overrideredirect(True)  # Rimuove la barra del titolo

        # Carica l'immagine dello splash screen
        #splash_image = Image.open("splash.jpg")
        splash_image = Image.open(resource_path("splash.jpg"))
        splash_photo = ImageTk.PhotoImage(splash_image)

        splash_label = tk.Label(self, image=splash_photo)
        splash_label.image = splash_photo
        splash_label.pack()

        # Centra lo splash screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - splash_image.width) // 2
        y = (screen_height - splash_image.height) // 2
        self.geometry(f'+{x}+{y}')

class AWSThread(threading.Thread):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.daemon = True
        self.running = threading.Event()
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            self.running.wait()
            if self.stop_event.is_set():
                break
            try:
                #self.manager.after(0, self.manager.show_loading, "Fetching instances...")
                instances = self.manager.aws_manager.list_ssm_instances()
                self.manager.after(0, self.manager.update_instances, instances)
                #is_connected = self.manager.aws_manager.check_connection()
                #self.manager.after(0, self.manager.update_connection_status, is_connected)
            except Exception as e:
                logger.error(f"Error in AWSThread: {str(e)}")
                self.manager.after(0, self.manager.show_error, f"Error: {str(e)}")
            #finally:
                #self.manager.after(0, self.manager.hide_loading)
            self.running.clear()

    def stop(self):
        self.stop_event.set()
        self.running.set()

class AWSSSMManagerApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="cosmo")
        # Imposta l'icona della finestra
        try:
            # Ottieni il widget root Tk sottostante
            root = self.master
            # Imposta l'icona per entrambi
            icon_path = resource_path('icon.ico')
            self.iconbitmap(resource_path('icon.ico'))
            root.iconbitmap(icon_path)
            # Opzionale: imposta anche l'icona per le finestre di dialogo
            self.tk.call('wm', 'iconphoto', self._w, tk.PhotoImage(file=resource_path('icon.ico')))
            
        except Exception as e:
            logger.warning(f"Impossibile caricare l'icona: {e}")
            
        self.withdraw()  # Nascondi la finestra principale
        self.splash = SplashScreen(self)
        self.loading_frame = None
        self.progress_bar = None
        
        self.active_connections = []
        self.aws_manager = AWSManager()
        self.aws_thread = None
        # Carica le preferenze prima di creare il menu
        self.load_preferences()
        
        # Crea il menu
        self.create_menu()
        
        # Avvia il caricamento dell'app in modo asincrono
        self.after(100, self.load_app)
    
    
    
    def create_menu(self):
        """Crea la barra dei menu principale."""
        menubar = Menu(self)
        self.config(menu=menubar)
        
        # Menu File
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Quit", command=self.on_closing)
        
        # Menu Settings
        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        # Aggiunta opzione per visualizzare i log
        settings_menu.add_command(label="View Logs", command=self.show_logs)        
        
        # Menu Help
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def show_about(self):
        """Mostra la finestra About."""
        about_window = ttk.Toplevel(self)
        about_window.title("About AWS SSM Manager")
        about_window.geometry("400x250")
        
        # Rendi la finestra modale
        about_window.transient(self)
        about_window.grab_set()
        
        # Frame principale
        frame = ttk.Frame(about_window, padding=20)
        frame.pack(fill='both', expand=True)
        
        # Titolo
        title_label = ttk.Label(frame, 
                              text="AWS SSM Manager", 
                              font=('Helvetica', 16, 'bold'))
        title_label.pack(pady=(0,10))
        
        # Sviluppatore
        dev_label = ttk.Label(frame, 
                            text="Developed by Mauro Arduini in his spare time.",
                            wraplength=350)
        dev_label.pack(pady=(0,20))
        
        # Links
        def create_link_label(frame, text, url):
            link = ttk.Label(frame, 
                           text=text,
                           cursor="hand2",
                           font=('Helvetica', 10, 'underline'),
                           foreground='blue')
            link.pack(pady=5)
            link.bind("<Button-1>", lambda e: webbrowser.open_new(url))
            return link
        
        # GitHub link
        create_link_label(frame, 
                         "GitHub Repository",
                         "https://github.com/mauroo82/ssm-manager")
        
        # LinkedIn link
        create_link_label(frame, 
                         "LinkedIn Profile",
                         "https://www.linkedin.com/in/mauro-arduini-0aa86621/")
        
        # Pulsante Chiudi
        close_button = ttk.Button(frame, 
                                text="Close", 
                                command=about_window.destroy,
                                style="primary")
        close_button.pack(pady=(20,0))
        
        # Centra la finestra
        about_window.update_idletasks()
        width = about_window.winfo_width()
        height = about_window.winfo_height()
        x = (about_window.winfo_screenwidth() // 2) - (width // 2)
        y = (about_window.winfo_screenheight() // 2) - (height // 2)
        about_window.geometry(f"{width}x{height}+{x}+{y}")
        
    
        
        
        
        
    def show_logs(self):
        """Mostra una finestra con i log recenti."""
        log_window = ttk.Toplevel(self)
        log_window.title("Application Logs")
        log_window.geometry("800x600")
        
        # Frame principale
        main_frame = ttk.Frame(log_window, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        # Aggiungi il messaggio informativo in alto
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill='x', pady=(0, 10))
        
        info_text = "Note: To change the log level, modify the 'log_level' value in preferences.json file."
        info_label = ttk.Label(
            info_frame, 
            text=info_text,
            font=('Helvetica', 9, 'italic'),
            foreground='gray'
        )
        info_label.pack(side='left', padx=5)
        
        # Area di testo per i log con scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        log_text = tk.Text(text_frame, wrap='word', yscrollcommand=scrollbar.set)
        log_text.pack(side='left', fill='both', expand=True)
        
        scrollbar.config(command=log_text.yview)
        
        # Bottoni per le azioni
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10,0))
        
        def refresh_logs():
            try:
                with open('app.log', 'r') as f:
                    logs = f.read()
                log_text.delete(1.0, tk.END)
                log_text.insert(tk.END, logs)
                log_text.see(tk.END)  # Scorre alla fine
            except Exception as e:
                log_text.delete(1.0, tk.END)
                log_text.insert(tk.END, f"Error reading log file: {str(e)}")
        
        def clear_logs():
            if Messagebox.yesno("Clear Logs", "Are you sure you want to clear the logs?"):
                try:
                    open('app.log', 'w').close()  # Pulisce il file
                    refresh_logs()
                    logger.info("Logs cleared by user")
                except Exception as e:
                    Messagebox.show_error(f"Error clearing logs: {str(e)}")
        
        def save_logs():
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".log",
                    filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
                    initialfile="app_logs.log"
                )
                if file_path:
                    with open('app.log', 'r') as source, open(file_path, 'w') as target:
                        target.write(source.read())
                    logger.info(f"Logs saved to {file_path}")
                    Messagebox.show_info("Logs saved successfully")
            except Exception as e:
                Messagebox.show_error(f"Error saving logs: {str(e)}")
        
        # Aggiunta bottoni
        ttk.Button(button_frame, text="Refresh", command=refresh_logs).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear Logs", command=clear_logs).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Save Logs", command=save_logs).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Close", command=log_window.destroy).pack(side='right', padx=5)
        
        # Carica i log iniziali
        refresh_logs()
        
        # Centra la finestra
        log_window.update_idletasks()
        width = log_window.winfo_width()
        height = log_window.winfo_height()
        x = (log_window.winfo_screenwidth() // 2) - (width // 2)
        y = (log_window.winfo_screenheight() // 2) - (height // 2)
        log_window.geometry(f"{width}x{height}+{x}+{y}")
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    # def hide_loading_frame(self):
    #     if self.loading_frame:
    #         self.loading_frame.destroy()
    #         self.loading_frame = None
    #         self.progress_bar = None
    def hide_loading_frame(self):
        if self.loading_frame:
            self.loading_frame.place_forget()
            self.progress_bar['value'] = 0
    def show_loading_frame(self):
        if self.loading_frame is None:
            self.loading_frame = ttk.Frame(self)
            self.loading_frame.place(relx=0.5, rely=0.5, anchor="center")
            self.progress_bar = Progressbar(self.loading_frame, bootstyle="success", maximum=100, length=300, mode='determinate')
            self.progress_bar.pack(padx=10, pady=10)
        else:
            self.loading_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.progress_bar['value'] = 0
        self.update_idletasks()
        self.update_loading_progress(0)
        
    def check_dependencies(self):
        error_found = False
        try:
            # Check AWS CLI
            subprocess.check_output(["aws", "--version"], stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info("AWS CLI is installed and working.")
        except (subprocess.CalledProcessError, OSError) as e:
            logger.error(f"Failed AWS CLI check: {str(e)}")
            self.show_error_popup("AWS CLI is not installed or not working. This application will not work without it.\n\n"
            "To install AWS CLI:\n"
            "1. Download the installer from: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html\n"
            "2. Run the installer and follow the prompts.\n"
            "3. Restart your computer after installation.\n"
            "4. Open a new command prompt and type 'aws --version' to verify the installation.")
            error_found = True

            # Controllo AWS SSM plugin
        try:
            subprocess.check_output(["aws", "ssm", "start-session", "--version"], stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info("AWS SSM plugin is installed and working.")
        except FileNotFoundError:
            logger.error("AWS SSM plugin not found. It might not be in the system PATH.")
            self.show_error_popup("AWS SSM plugin is not installed or not in the system PATH. This application will not work without it.\n\n"
            "To install AWS SSM plugin:\n"
            "1. Download the plugin from: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html\n"
            "2. Follow the installation instructions for your operating system.\n"
            "3. Ensure the installation directory is added to your system PATH.\n"
            "4. Restart your computer after installation.\n"
            "5. Open a new command prompt and type 'aws ssm start-session --version' to verify the installation.")
            error_found = True
        except (subprocess.CalledProcessError, OSError) as e:
            logger.error(f"Failed AWS SSM plugin check: {str(e)}")
            self.show_error_popup("There was an error checking the AWS SSM plugin. Please ensure it's correctly installed and your system PATH is set up properly.")
            error_found = True

        return not error_found
            
    def show_error_popup(self, message):
        # Create a new popup window
        popup = tk.Toplevel(self)
        popup.title("Dependency Error")
        
        # Set the window size and disable resizing
        popup.geometry("500x500")
        popup.resizable(False, False)

        text_widget = tk.Text(popup, wrap=tk.WORD, font=("Arial", 10))
        text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        text_widget.insert(tk.END, message)
        text_widget.config(state=tk.DISABLED)

        close_button = ttk.Button(popup, text="Close Application", command=self.quit)
        close_button.pack(pady=10)

        popup.protocol("WM_DELETE_WINDOW", self.quit)
            
    def load_app(self):
        print("Iniziando load_app")
        print("Verifico dipendenze")
        if not self.check_dependencies():  # Se ci sono errori, non continuare a caricare l'app
            print("Errore nelle dipendenze. L'applicazione verrà terminata.")
            #self.after(3000, self.destroy)  # Chiudi l'applicazione dopo 3 secondi
            return
        if self.splash:  # Destroy splash screen if it exists
            self.splash.destroy()
        self.deiconify()  # Show the main window after the checks
        # Esegui qui tutte le operazioni di inizializzazione
        style = ttk.Style()
        self.configure_styles(style)
        
        self.title("AWS SSM Manager")
        self.geometry("1200x650")
        self.bind('<Configure>', self.on_window_resize)

        self.load_preferences()
        print("Creazione dei widget")
        self.create_widgets()
        print("Widget creati")
        if self.aws_thread is None:
            self.aws_thread = AWSThread(self)
            self.aws_thread.start()

        # Quando tutto è pronto, chiudi lo splash screen e mostra l'app
        self.after(0, self.show_app)

    def show_app(self):
        self.splash.destroy()
        self.deiconify()  # Mostra la finestra principale
        
    # def on_closing(self):
    #     if Messagebox.yesno("Quit", "Do you want to quit?"):
    #         if self.aws_thread:
    #             self.aws_thread.stop()
    #             self.aws_thread.join()
    #         self.destroy()    

    def configure_styles(self, style):
                
        #ssh.TButton
        style.configure("SSH.TButton", 
                background="black", 
                foreground="white", 
                bordercolor="black",
                lightcolor="black",
                darkcolor="black",
                focuscolor="black")
        
        style.map("SSH.TButton",
                background=[('active', 'black')],
                bordercolor=[('active', 'black')],
                lightcolor=[('active', 'black')],
                darkcolor=[('active', 'black')])
                
        #custom.TButton
        style.configure("Custom.TButton", 
                background="purple", 
                foreground="white", 
                bordercolor="purple",
                lightcolor="purple",
                darkcolor="purple",
                focuscolor="purple")
        
        style.map("Custom.TButton",
                background=[('active', 'purple')],
                bordercolor=[('active', 'purple')],
                lightcolor=[('active', 'purple')],
                darkcolor=[('active', 'purple')])

        #host.TButton      
        style.map("Host.TButton",
                background=[('active', 'brown')],
                bordercolor=[('active', 'brown')],
                lightcolor=[('active', 'brown')],
                darkcolor=[('active', 'brown')])
        
        style.configure("Host.TButton", 
                background="brown", 
                foreground="white", 
                bordercolor="brown",
                lightcolor="brown",
                darkcolor="brown",
                focuscolor="brown")
        
        #Termina.TButton
        style.configure("Termina.TButton", 
                background="red", 
                foreground="white", 
                bordercolor="red",
                lightcolor="red",
                darkcolor="red",
                focuscolor="red")
        
        style.map("Termina.TButton",
                background=[('active', 'red')],
                bordercolor=[('active', 'red')],
                lightcolor=[('active', 'red')],
                darkcolor=[('active', 'red')])
        
        # style.configure("CustomProgressbar.Horizontal", 
        #             background="green",  # Sfondo della barra
        #             troughcolor="white")  # Colore del fondo della barra
        
        style.configure("Instance.TFrame", background="white", bordercolor="light gray", relief="solid")
        style.configure("ProfileRegion.TFrame", background="white", bordercolor="light gray", relief="solid", borderwidth=1)
        style.configure("ActiveConnections.TFrame", background="white", bordercolor="light gray", relief="solid", borderwidth=1)
        
        self.title("AWS SSM Manager")
        self.geometry("1200x650")
        self.aws_manager = AWSManager()
        self.aws_thread = AWSThread(self)
        self.bind('<Configure>', self.on_window_resize)
        # # Carica le icone per SSH e RDP
        # self.ssh_icon = tk.PhotoImage(file="image/ssh.png")
        # self.rdp_icon = tk.PhotoImage(file="image/rdp.png")
        # Carica e ridimensiona le icone per SSH e RDP
        # self.ssh_icon = self.load_icon("image/ssh.png", (20, 20))
        # self.rdp_icon = self.load_icon("image/rdp.png", (20, 20))

        self.load_preferences()
        #self.create_widgets()
        self.aws_thread.start()

    def load_icon(self, path, size):
        #"""Funzione per caricare e ridimensionare un'immagine."""
        image = Image.open(path)
        image = image.resize(size, Image.LANCZOS)  # Sostituisci ANTIALIAS con LANCZOS
        return ImageTk.PhotoImage(image)

    def create_widgets(self):
        print("Iniziando create_widgets")
        # Frame principale
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=BOTH, expand=True)

        # Frame per profilo e regione (in alto)
        self.create_profile_region_inputs(main_frame)

        # Frame per le istanze (al centro)
        self.create_instances_frame(main_frame)
        #spacer_frame = ttk.Frame(main_frame, height=20)  # Altezza regolabile per maggiore o minore spazio
        #spacer_frame.pack(fill=X)
        # Frame per le connessioni attive (in basso)
        self.create_active_connections_frame(main_frame)

        # Label di caricamento (in fondo)
        self.create_loading_label(main_frame)
        #self.copy_icon = ImageTk.PhotoImage(Image.open("copy_icon.png").resize((15, 15), Image.LANCZOS))
        print("Fine create_widgets")

    # def create_profile_region_inputs(self, parent):
    #     input_frame = ttk.Frame(parent, style="ProfileRegion.TFrame")
    #     input_frame.pack(pady=10, padx=10, fill=X)

    #     ttk.Label(input_frame, text="Profile:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
    #     self.profile_var = ttk.StringVar(value=self.preferences.get('profile', ''))
    #     self.profile_combo = ttk.Combobox(input_frame, textvariable=self.profile_var, width=15, state="readonly")
    #     self.profile_combo['values'] = self.aws_manager.get_profiles()
    #     self.profile_combo.grid(row=0, column=1, padx=5, pady=5, sticky=EW)

    #     ttk.Label(input_frame, text="Region:").grid(row=0, column=2, padx=5, pady=5, sticky=W)
    #     self.region_var = ttk.StringVar(value=self.preferences.get('region', ''))
    #     self.region_combo = ttk.Combobox(input_frame, textvariable=self.region_var, width=15, state="readonly")
    #     self.region_combo['values'] = self.aws_manager.get_regions()
    #     self.region_combo.grid(row=0, column=3, padx=5, pady=5, sticky=EW)

    #     set_button = ttk.Button(input_frame, text="Connect", command=self.set_profile_and_region, bootstyle=SUCCESS)
    #     set_button.grid(row=0, column=4, padx=5, pady=5)
        
    #     disconnect_button = ttk.Button(input_frame, text="Disconnect", command=self.disconnect_profile_and_region, bootstyle=DANGER)
    #     disconnect_button.grid(row=0, column=6, padx=5, pady=5)
        
    #     refresh_button = ttk.Button(input_frame, text="Refresh", command=self.refresh_profiles_and_regions)
    #     refresh_button.grid(row=0, column=7, padx=5, pady=5)

    #     self.status_icon = ttk.Label(input_frame, text="⚫", font=('Arial', 16))
    #     self.status_icon.grid(row=0, column=8, padx=5, pady=5)

    #     input_frame.columnconfigure(1, weight=1)
    #     input_frame.columnconfigure(3, weight=1)
        
    def create_profile_region_inputs(self, parent):
        input_frame = ttk.Frame(parent, style="ProfileRegion.TFrame")
        input_frame.pack(pady=10, padx=10, fill=X)

        ttk.Label(input_frame, text="Profile:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.profile_var = ttk.StringVar(value=self.preferences.get('profile', ''))
        self.profile_combo = ttk.Combobox(input_frame, textvariable=self.profile_var, width=15, state="readonly")
        self.profile_combo['values'] = self.aws_manager.get_profiles()
        self.profile_combo.grid(row=0, column=1, padx=5, pady=5, sticky=EW)

        ttk.Label(input_frame, text="Region:").grid(row=0, column=2, padx=5, pady=5, sticky=W)
        self.region_var = ttk.StringVar(value=self.preferences.get('region', ''))
        self.region_combo = ttk.Combobox(input_frame, textvariable=self.region_var, width=15, state="readonly")
        self.region_combo['values'] = self.aws_manager.get_regions()
        self.region_combo.grid(row=0, column=3, padx=5, pady=5, sticky=EW)

        # Configura il pulsante con la funzione di connessione
        self.connect_button = ttk.Button(
            input_frame,
            text="Connect",
            command=self.toggle_connection,
            bootstyle=SUCCESS
        )
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)

        refresh_button = ttk.Button(input_frame, text="Refresh", command=self.refresh_profiles_and_regions)
        refresh_button.grid(row=0, column=5, padx=5, pady=5)

        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)
        
    def toggle_connection(self):
        if self.connect_button['text'] == "Connect":
            try:
                # Tenta di impostare il profilo e la regione
                self.set_profile_and_region()
                # Se la connessione ha successo, aggiorna il pulsante
                self.connect_button.config(text="Disconnect", bootstyle=DANGER)
            except Exception:
                # Riporta il pulsante allo stato iniziale e mostra il messaggio di errore
                self.connect_button.config(text="Connect", bootstyle=SUCCESS)
                Messagebox.show_error(
                    "Errore nella connessione. Verifica le autorizzazioni o il login.",
                    title="Errore di Connessione"
                )
        else:
            # Esegui disconnessione e resetta il pulsante
            self.disconnect_profile_and_region()
            self.connect_button.config(text="Connect", bootstyle=SUCCESS)

            

    def disconnect_profile_and_region(self):
        # Scollega il profilo e la regione
        self.aws_manager.disconnect_profile_and_region()  # Assicurati che il tuo AWSManager gestisca questa operazione

        # Resetta le variabili del profilo e della regione
        self.profile_var.set("")  # Reset profilo a vuoto
        self.region_var.set("")    # Reset regione a vuoto

        # Termina eventuali sessioni attive
        for conn in self.active_connections[:]:  # Usa una copia della lista per evitarne la modifica durante l'iterazione
            self.terminate_connection(conn)
            
        # Resetta le istanze nel frame
        self.update_instances([])  # Passa una lista vuota per rimuovere tutte le istanze

        # Resetta la barra di progresso
        #self.progress_bar.configure(value=0)  # Assicurati che la barra parta da 0
        #self.progress_bar.pack_forget()  # Nasconde la barra di progresso

        # Aggiorna l'interfaccia utente per riflettere la disconnessione
        logger.info("Disconnected from profile and region.")
        self.show_error("Disconnected from profile and region.")
    
    def refresh_profiles_and_regions(self):
        self.profile_combo['values'] = self.aws_manager.get_profiles()
        self.region_combo['values'] = self.aws_manager.get_regions()
        
    # def create_instances_frame(self, parent):
    #     self.outer_frame = ttk.Frame(parent)
    #     self.outer_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    #     # Crea l'header
    #     self.header_frame = ttk.Frame(self.outer_frame)
    #     self.header_frame.pack(fill=X)

    #     headers = ["Name", "ID", "Type", "OS", "State", "Actions"]
    #     widths = [30, 18, 10, 10, 13, 60]  # Larghezze approssimative per ogni colonna
    #     for i, header in enumerate(headers):
    #         ttk.Label(self.header_frame, text=header, font=('Arial', 10, 'bold'), width=widths[i], anchor="w").pack(side=LEFT, padx=2, fill=X, expand=True)

    #     # Crea il canvas scrollabile per le istanze
    #     self.instances_canvas = ttk.Canvas(self.outer_frame)
    #     self.instances_canvas.pack(side=LEFT, fill=BOTH, expand=True)

    #     self.scrollbar = ttk.Scrollbar(self.outer_frame, orient=VERTICAL, command=self.instances_canvas.yview)
    #     self.scrollbar.pack(side=RIGHT, fill=Y)

    #     self.instances_canvas.configure(yscrollcommand=self.scrollbar.set)

    #     self.instances_frame = ttk.Frame(self.instances_canvas)
    #     self.instances_canvas.create_window((0, 0), window=self.instances_frame, anchor="nw", tags="instance_frame")
        
    #     self.instances_canvas.bind('<Configure>', self.on_canvas_configure)
    #     self.instances_frame.bind('<Configure>', lambda e: self.instances_canvas.configure(scrollregion=self.instances_canvas.bbox("all")))    
    def create_instances_frame(self, parent):
        # Frame esterno con bordo
        outer_container = ttk.Frame(parent, style="ProfileRegion.TFrame")
        outer_container.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Aggiungi il titolo
        title_label = ttk.Label(outer_container, text="List Instances", font=('Arial', 12, 'bold'))
        title_label.pack(anchor=W, padx=10, pady=(10, 5))  # Allineato a sinistra
        
        # Frame interno con padding per mostrare il bordo
        self.outer_frame = ttk.Frame(outer_container)
        self.outer_frame.pack(fill=BOTH, expand=True, padx=1, pady=1)

        # Il resto del codice rimane uguale
        self.header_frame = ttk.Frame(self.outer_frame)
        self.header_frame.pack(fill=X)

        headers = ["Name", "ID", "Type", "OS", "State", "Actions"]
        widths = [30, 18, 10, 10, 13, 60]
        for i, header in enumerate(headers):
            ttk.Label(self.header_frame, text=header, font=('Arial', 10, 'bold'), width=widths[i], anchor="w").pack(side=LEFT, padx=2, fill=X, expand=True)

        self.instances_canvas = ttk.Canvas(self.outer_frame)
        self.instances_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.outer_frame, orient=VERTICAL, command=self.instances_canvas.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        self.instances_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.instances_frame = ttk.Frame(self.instances_canvas)
        self.instances_canvas.create_window((0, 0), window=self.instances_frame, anchor="nw", tags="instance_frame")
        
        self.instances_canvas.bind('<Configure>', self.on_canvas_configure)
        self.instances_frame.bind('<Configure>', lambda e: self.instances_canvas.configure(scrollregion=self.instances_canvas.bbox("all")))
        
    def on_canvas_configure(self, event):
        # Aggiorna la larghezza del frame interno quando il canvas viene ridimensionato
        self.instances_canvas.itemconfig("instance_frame", width=event.width)
        self.instances_canvas.configure(scrollregion=self.instances_canvas.bbox("all"))
    # def hide_progress_bar(self):
    #     if self.progress_bar:
    #         self.progress_bar.pack_forget()  # Nasconde la barra di progresso

    def create_loading_label(self, parent):
        self.loading_label = ttk.Label(parent, text="", font=('Arial', 10, 'bold'))
        self.loading_label.pack(pady=5)

    # def update_connection_status(self, is_connected):
    #     if is_connected:
    #         self.status_icon.config(text="🟢", foreground="green")
    #     else:
    #         self.status_icon.config(text="🔴", foreground="red")


    def update_instances(self, instances):
            # Pulisci il frame delle istanze
        for widget in self.instances_frame.winfo_children():
            widget.destroy()

            # Se non ci sono istanze, mostra un messaggio di errore e interrompi
        if instances is None:
            self.connect_button.config(text="Connect", bootstyle=SUCCESS)
            self.show_error("Errore nella connessione. Verifica le autorizzazioni o il login.")
            return
        
        for i, instance in enumerate(instances):
            frame = ttk.Frame(self.instances_frame, relief=RAISED, borderwidth=1, style="Instance.TFrame")
            frame.pack(fill=X, expand=True, padx=5, pady=5)

            # Creiamo un container frame per mantenere l'allineamento
            container_frame = ttk.Frame(frame)
            container_frame.pack(fill=X, expand=True, side=LEFT, padx=2)

            # Larghezze fisse per ogni colonna
            widths = {
                'name': 32,
                'id': 20,
                'type': 11,
                'os': 15,
                'state': 13
            }

            # Creiamo le label con larghezze fisse nel container
            ttk.Label(container_frame, text=f" | ", anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f"{instance.get('name', 'N/A')}", width=widths['name'], anchor="w").pack(side=LEFT)
            #ttk.Label(container_frame, text=f"{instance.get('id', 'N/A')}", width=widths['id'], anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f" | ", anchor="w").pack(side=LEFT)

             # ID dell'istanza con pulsante di copia
            instance_id = instance.get('id', 'N/A')
            id_frame = ttk.Frame(container_frame)  # Nuovo frame per l'ID e il pulsante di copia
            id_frame.pack(side=LEFT)

            # Label dell'ID
            #id_label = ttk.Label(id_frame, text=instance_id, width=widths['id'], anchor="w")
            #id_label.pack(side=LEFT)

            # Bottone per copiare l'ID
            copy_button = ttk.Button(
                id_frame, 
                #image=self.copy_icon, 
                text=instance_id,
                command=lambda id=instance_id: self.copy_to_clipboard(id), 
                style="light"
            )
            copy_button.pack(side=LEFT, padx=0)
            
            
            ttk.Label(container_frame, text=f" | ", anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f"{instance.get('type', 'N/A')}", width=widths['type'], anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f" | ", anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f"{instance.get('os', 'N/A')}", width=widths['os'], anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f" | ", anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f"{instance.get('state', 'N/A')}", width=widths['state'], anchor="w").pack(side=LEFT)
            ttk.Label(container_frame, text=f" | ", anchor="w").pack(side=LEFT)

            # Frame per i pulsanti
            button_frame = ttk.Frame(frame)
            button_frame.pack(side=RIGHT, padx=5, pady=5)

            # Pulsanti
            ttk.Button(button_frame, text="SSH", command=lambda id=instance.get('id'): self.start_ssh_session(id), style="dark", width=8).pack(side=LEFT, padx=2)
            ttk.Button(button_frame, text="RDP", command=lambda id=instance.get('id'): self.start_rdp_session(id), style="primary", width=8).pack(side=LEFT, padx=2)
            ttk.Button(button_frame, text="CUSTOM", command=lambda id=instance.get('id'): self.open_custom_port_popup(id), style="Custom.TButton", width=8).pack(side=LEFT, padx=2)
            ttk.Button(button_frame, text="HOST", command=lambda id=instance.get('id'): self.open_host_popup(id), style="success", width=8).pack(side=LEFT, padx=2)

        self.instances_canvas.update_idletasks()
        self.instances_canvas.configure(scrollregion=self.instances_canvas.bbox("all"))
    # def update_instances(self, instances):
    #     for widget in self.instances_frame.winfo_children():
    #         widget.destroy()

    #     for i, instance in enumerate(instances):
    #         frame = ttk.Frame(self.instances_frame, relief=RAISED, borderwidth=1, style="Instance.TFrame")
    #         frame.pack(fill=X, expand=True, padx=5, pady=5)

    #         # Creiamo un sottoriquadro per le informazioni
    #         info_frame = ttk.Frame(frame)
    #         info_frame.pack(side=LEFT, fill=X, expand=True)
            
    #         # info_frame = ttk.Frame(frame)
    #         # info_frame.pack(side=LEFT, fill=X, expand=True, padx=5, pady=5)

    #         # Disponiamo le informazioni in due righe
    #         ttk.Label(info_frame, text=f"{instance.get('name', 'N/A')}",  width=32, anchor="w").pack(side=LEFT, padx=2, fill=X, expand=True)
    #         ttk.Label(info_frame, text=f"{instance.get('id', 'N/A')}",    width=20, anchor="w").pack(side=LEFT, padx=2)
    #         # copy_button = ttk.Button(info_frame, text="Copia", command=lambda: self.copy_to_clipboard(instances))
    #         # copy_button.pack(side=LEFT, padx=5)
            
    #         ttk.Label(info_frame, text=f"{instance.get('type', 'N/A')}",  width=11, anchor="w").pack(side=LEFT, padx=2)
    #         ttk.Label(info_frame, text=f"{instance.get('os', 'N/A')}",    width=15, anchor="w").pack(side=LEFT, padx=2)
    #         ttk.Label(info_frame, text=f"{instance.get('state', 'N/A')}", width=13, anchor="w").pack(side=LEFT, padx=2)

    #         # Creiamo un sottoriquadro per i pulsanti
    #         button_frame = ttk.Frame(frame)
    #         button_frame.pack(side=RIGHT, padx=5, pady=5)

    #         # ttk.Button(button_frame, text="SSH", command=lambda id=instance.get('id'): self.start_ssh_session(id), style="SSH.TButton", width=8).pack(side=LEFT, padx=2)
    #         # ttk.Button(button_frame, text="RDP", command=lambda id=instance.get('id'): self.start_rdp_session(id), width=8).pack(side=LEFT, padx=2)
    #         # ttk.Button(button_frame, text="CUSTOM", command=lambda id=instance.get('id'): self.open_custom_port_popup(id), style="Custom.TButton", width=8).pack(side=LEFT, padx=2)
    #         # ttk.Button(button_frame, text="HOST", command=lambda id=instance.get('id'): self.open_host_popup(id), style="Host.TButton", width=8).pack(side=LEFT, padx=2)

    #         ttk.Button(button_frame, text="SSH", command=lambda id=instance.get('id'): self.start_ssh_session(id), style="dark", width=8).pack(side=LEFT, padx=2)
    #         ttk.Button(button_frame, text="RDP", command=lambda id=instance.get('id'): self.start_rdp_session(id), style="primary", width=8).pack(side=LEFT, padx=2)
    #         ttk.Button(button_frame, text="CUSTOM", command=lambda id=instance.get('id'): self.open_custom_port_popup(id), style="Custom.TButton", width=8).pack(side=LEFT, padx=2)
    #         ttk.Button(button_frame, text="HOST", command=lambda id=instance.get('id'): self.open_host_popup(id), style="success", width=8).pack(side=LEFT, padx=2)
        
    #     self.instances_canvas.update_idletasks()
    #     self.instances_canvas.configure(scrollregion=self.instances_canvas.bbox("all"))


    def copy_to_clipboard(self, instance_id):
        self.clipboard_clear()
        self.clipboard_append(instance_id)
        self.update()  # Aggiorna la clipboard per renderla persistente
        Messagebox.show_info(f"Copied ID: {instance_id}", "Clipboard")
    
# Aggiungi questo metodo per gestire il ridimensionamento della finestra
    def on_window_resize(self, event=None):
        if hasattr(self, 'instances_canvas'):
            self.instances_canvas.configure(scrollregion=self.instances_canvas.bbox("all"))

    def open_host_popup(self, instance_id):
        popup = tk.Toplevel(self)
        popup.title("Host Port Forwarding")
        popup.geometry("300x300")

        ttk.Label(popup, text="Remote Host:").pack(pady=5)
        remote_host_entry = ttk.Entry(popup)
        remote_host_entry.pack(pady=5)

        ttk.Label(popup, text="Remote Port:").pack(pady=5)
        remote_port_entry = ttk.Entry(popup)
        remote_port_entry.pack(pady=5)

        def start_host_forwarding():
            remote_host = remote_host_entry.get()
            remote_port = remote_port_entry.get()
            local_port = self.find_free_port()
            profile = self.profile_var.get()
            region = self.region_var.get()

            aws_command = f"aws ssm start-session --region {region} --target {instance_id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=\"{remote_host}\",portNumber=\"{remote_port}\",localPortNumber=\"{local_port}\" --profile {profile}"

            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                process = subprocess.Popen(aws_command, 
                                        shell=True, 
                                        startupinfo=startupinfo, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
                
                self.active_connections.append({
                    'instance_id': instance_id,
                    'type': 'Host',
                    'remote_host': remote_host,
                    'remote_port': remote_port,
                    'port': local_port,
                    'process': process
                })
                self.update_active_connections()
                
                logger.info(f"Host port forwarding started for instance {instance_id} (Remote: {remote_host}:{remote_port}, Local: {local_port})")
                Messagebox.show_info(f"Host port forwarding started.\nRemote: {remote_host}:{remote_port}\nLocal port: {local_port}", "Host Port Forwarding")
                popup.destroy()
            except Exception as e:
                logger.error(f"Failed to start host port forwarding: {str(e)}")
                self.show_error(f"Failed to start host port forwarding: {str(e)}")

        ttk.Button(popup, text="Start Forwarding", command=start_host_forwarding).pack(pady=10)
    
    
    def open_custom_port_popup(self, instance_id):
        remote_port = Querybox.get_integer(
            prompt="Enter the remote port number:",
            title="Custom Port Forwarding",
            initialvalue=80,
            minvalue=1,
            maxvalue=65535
        )
        
        if remote_port is not None:
            local_port = self.find_free_port()
            profile = self.profile_var.get()
            region = self.region_var.get()
            
            aws_command = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters portNumber={remote_port},localPortNumber={local_port} --region {region} --profile {profile}"
            
            try:
                # Configurazione per nascondere la finestra
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                process = subprocess.Popen(aws_command, 
                                        shell=True, 
                                        startupinfo=startupinfo, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
                
                self.active_connections.append({
                    'instance_id': instance_id,
                    'type': 'Custom',
                    #'remote_port': remote_port,
                    'port': local_port,
                    'process': process
                })
                self.update_active_connections()
                
                logger.info(f"Custom port forwarding started for instance {instance_id} (Remote: {remote_port}, Local: {local_port})")
                Messagebox.show_info(f"Port forwarding started.\nRemote port: {remote_port}\nLocal port: {local_port}", "Custom Port Forwarding")
            except Exception as e:
                logger.error(f"Failed to start custom port forwarding: {str(e)}")
                self.show_error(f"Failed to start custom port forwarding: {str(e)}")

    def create_active_connections_frame(self, parent):
        frame = ttk.Frame(parent, style="ActiveConnections.TFrame")
        frame.pack(fill=X, padx=10, pady=10)  # Usa self.outer_frame invece di self.instances_frame

        ttk.Label(frame, text="Active Connections", font=('Arial', 12, 'bold')).pack(anchor=W, pady=1)

        # Create a canvas to hold the connections
        self.connections_canvas = ttk.Canvas(frame)
        self.connections_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        # self.connections_frame = ttk.Frame(frame)
        # self.connections_frame.pack(fill=X, expand=True)
        
        self.scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=self.connections_canvas.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        
        self.connections_canvas.configure(yscrollcommand=self.scrollbar.set)

        # Create a frame inside the canvas
        # self.connections_frame = ttk.Frame(self.connections_canvas)
        # self.connections_canvas.create_window((0, 0), window=self.connections_frame, anchor="nw")
        
        # Create a frame inside the canvas
        self.connections_frame = ttk.Frame(self.connections_canvas)
        self.connections_canvas.create_window((0, 0), window=self.connections_frame, anchor="nw", tags="connections_frame")


        # Bind canvas size to connections
        #self.connections_canvas.bind('<Configure>', lambda e: self.connections_canvas.configure(scrollregion=self.connections_canvas.bbox("all")))
        self.connections_canvas.bind('<Configure>', self.on_connections_canvas_configure)
        self.connections_frame.bind('<Configure>', lambda e: self.connections_canvas.configure(scrollregion=self.connections_canvas.bbox("all")))
        # Inizializza la lista delle connessioni (vuota all'inizio)
        self.update_active_connections()

        # Crea la barra di caricamento Floodgauge sotto il frame delle connessioni
        # self.loading_progress = Progressbar(frame, bootstyle="success")
        # self.loading_progress.pack(pady=10)
    def on_connections_canvas_configure(self, event):
        # Aggiorna la larghezza del frame interno quando il canvas viene ridimensionato
        self.connections_canvas.itemconfig("connections_frame", width=event.width)
    # Aggiungi il metodo per aggiornare la barra di caricamento
    def update_loading_progress(self, current_value):
        if self.progress_bar:
            if current_value <= 100:
                self.progress_bar['value'] = current_value
                self.update_idletasks()
                self.after(100, lambda: self.update_loading_progress(current_value + 10))
            else:
                self.hide_loading_frame()
            
    def update_active_connections(self):
        if not hasattr(self, 'connections_frame'):
            return

        for widget in self.connections_frame.winfo_children():
            widget.destroy()

        for conn in self.active_connections:
            conn_frame = ttk.Frame(self.connections_frame)
            #conn_frame.pack(fill=X, pady=2, expand=True)
            conn_frame.pack(fill=X, pady=4, expand=True)  # Aumentato il pady per più spazio verticale
            
            # Frame principale per contenuto e progress bar
            content_frame = ttk.Frame(conn_frame)
            #content_frame.pack(fill=X, expand=True)
            content_frame.pack(fill=X, expand=True, padx=10)  # Aggiunto padding orizzontale
            # Progress bar (inizialmente nascosta)
            progress_frame = ttk.Frame(conn_frame)
            progress = Progressbar(
            progress_frame, 
            bootstyle="success",
            mode='indeterminate',
            length=200
            )
            
            conn_type = conn.get('type', 'Unknown')
            port = conn.get('port', 'N/A')
            label_text = f"Instance: {conn['instance_id']},  Type: {conn_type},  Port: {port}"
            
            if conn_type == 'Host':
                remote_host = conn.get('remote_host', 'N/A')
                remote_port = conn.get('remote_port', 'N/A')
                label_text = f"Instance: {conn['instance_id']},  Type: {conn_type},  Remote: {remote_host}:{remote_port},  Local Port: {port}"
            
            #ttk.Label(conn_frame, text=label_text, ).pack(side=LEFT, fill=X, expand=True)
            ttk.Label(content_frame, text=label_text, font=('Helvetica', 11, ), width=80, padding=(10,5)).pack(side=LEFT, fill=X, expand=True, padx=20)
            #ttk.Button(conn_frame, text="Termina", command=lambda c=conn: self.terminate_connection(c), style="danger").pack(side=RIGHT)

            
            def terminate_with_loading(connection=conn, 
                                        content=content_frame, 
                                        progress_f=progress_frame, 
                                        prog=progress):
                    # Nascondi il contenuto normale e mostra la barra di progresso
                    content.pack_forget()
                    progress_f.pack(fill=X, expand=True, pady=10)
                    prog.pack(padx=20)
                    prog.start()
                    
                    # Usa after per eseguire la terminazione in modo asincrono
                    self.after(100, lambda: self._perform_termination(connection, content, progress_f))

            ttk.Button(
                content_frame, 
                text="END", 
                command=terminate_with_loading,
                style="danger"
            ).pack(side=RIGHT)
            
            
        self.connections_canvas.update_idletasks()
        self.connections_canvas.configure(scrollregion=self.connections_canvas.bbox("all"))
    
    def _perform_termination(self, connection, content_frame, progress_frame):
        """Esegue la terminazione effettiva della connessione."""
        try:
            process = connection['process']
            
            if process.poll() is None:  # Se il processo è ancora in esecuzione
                # Ottieni il PID del processo PowerShell
                powershell_pid = process.pid
                
                try:
                    parent = psutil.Process(powershell_pid)
                    children = parent.children(recursive=True)
                    
                    # Termina i processi figli
                    for child in children:
                        try:
                            child.terminate()
                            child.wait(timeout=5)
                        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                            child.kill() if child.is_running() else None
                    
                    # Termina il processo genitore
                    parent.terminate()
                    try:
                        parent.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        parent.kill()

                    # Breve attesa per assicurarsi che tutto sia terminato
                    time.sleep(2)

                    # Chiudi eventuali finestre associate
                    def close_window(hwnd, _):
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            if pid == powershell_pid:
                                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        except:
                            pass
                    
                    win32gui.EnumWindows(close_window, None)
                    
                except psutil.NoSuchProcess:
                    logger.warning(f"Process no longer exists (pid={powershell_pid})")
            
            # Rimuovi la connessione e aggiorna l'interfaccia
            if connection in self.active_connections:
                self.active_connections.remove(connection)
                logger.info(f"Connection terminated for instance {connection['instance_id']}")
                
            # Aggiorna l'interfaccia dopo un breve delay per mostrare l'animazione
            self.after(1000, self.update_active_connections)
                
        except Exception as e:
            logger.error(f"Error terminating connection: {str(e)}")
            # Ripristina l'interfaccia in caso di errore
            content_frame.pack()
            progress_frame.pack_forget()
            self.show_error(f"Error terminating connection: {str(e)}")
            
            
            
            
    def set_profile_and_region(self):
        profile = self.profile_var.get()
        region = self.region_var.get()
        try:
            self.aws_manager.set_profile_and_region(profile, region)
            logger.info(f"Profile and region set: {profile}, {region}")
            
                    # Mostra il frame di caricamento
                    # Mostra il frame di caricamento
            self.after(100, self.show_loading_frame)
            # self.progress_bar.configure(value=0)  # Assicurati che parta da 0
            # self.progress_bar.pack(pady=10, anchor="center", fill=X)  # Assicurati che sia visibile
            # # Mostra la barra di caricamento e inizia a aggiornarla
            # for progress in range(0, 101, 20):  # Simula il progresso
            #     self.progress_bar.configure(value=progress)
            #     self.update_idletasks()  # Aggiorna l'interfaccia utente
            #     self.after(500)  # Ritardo per vedere l'aggiornamento
            
            # Attiva il thread AWS per aggiornare le istanze
            self.aws_thread.running.set()
            self.save_preferences()
            
            # Resetta la barra di caricamento alla fine
            #self.progress_bar.configure(value=0)
            # Nascondi la barra di progresso
            #self.hide_progress_bar()
            
        except ValueError as e:
            logger.error(f"Error setting profile and region: {str(e)}")
            self.show_error(f"Failed to set profile and region: {str(e)}")

    def start_ssh_session(self, instance_id):
        try:
            profile = self.profile_var.get()
            region = self.region_var.get()
            aws_command = f"aws ssm start-session --target {instance_id} --region {region} --profile {profile}"
            
            # Usa cmd.exe invece di PowerShell
            cmd_command = f'cmd.exe /K "{aws_command}"'
            
            process = subprocess.Popen(cmd_command, creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            self.active_connections.append({
                'instance_id': instance_id,
                'type': 'SSH',
                'process': process
            })
            self.update_active_connections()
            logger.info(f"SSH session started for instance {instance_id} in a new CMD window")
            
            # Start the monitor after adding an SSH session
            self.monitor_connections()
        except Exception as e:
            logger.error(f"Failed to start SSH session: {str(e)}")
            self.show_error(f"Failed to start SSH session: {str(e)}")

    def monitor_connections(self):
        def check_connections():
            while True:
                for conn in self.active_connections[:]:
                    if conn['process'].poll() is not None:  # Process has ended
                        self.active_connections.remove(conn)
                        self.update_active_connections()
                time.sleep(2)  # Wait for 5 seconds before checking again

        threading.Thread(target=check_connections, daemon=True).start()

    def find_free_port(self, start=60000, end=60100):
        while True:
            port = random.randint(start, end)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except socket.error:
                    continue

    def start_rdp_session(self, instance_id):
        try:
            local_port = self.find_free_port()
            profile = self.profile_var.get()
            region = self.region_var.get()
            aws_command = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters portNumber=3389,localPortNumber={local_port} --region {region} --profile {profile}"
            
            # Utilizziamo subprocess.STARTUPINFO per nascondere la finestra
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # process = subprocess.Popen(["powershell", "-Command", aws_command], 
            # creationflags=subprocess.CREATE_NEW_CONSOLE)

            process = subprocess.Popen(["powershell", "-Command", aws_command],
                            startupinfo=startupinfo,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
            
            self.after(2000)  # Attendi 2 secondi
            
            rdp_command = f"mstsc /v:localhost:{local_port}"
            subprocess.Popen(rdp_command, shell=False)
            
            self.active_connections.append({
                'instance_id': instance_id,
                'type': 'RDP',
                'port': local_port,
                'process': process
            })
            self.update_active_connections()
            logger.info(f"RDP session started for instance {instance_id} on local port {local_port}")
        except Exception as e:
            logger.error(f"Failed to start RDP session: {str(e)}")
            self.show_error(f"Failed to start RDP session: {str(e)}")

    def terminate_connection(self, connection):
        try:
            process = connection['process']
            
            if process.poll() is None:  # Se il processo è ancora in esecuzione
                # Ottieni il PID del processo PowerShell
                powershell_pid = process.pid
                
                # Trova tutti i processi figli
                # Trova tutti i processi figli (es. processo AWS SSM)
                try:
                    parent = psutil.Process(powershell_pid)
                except psutil.NoSuchProcess:
                    logger.warning(f"Process no longer exists (pid={powershell_pid})")
                    self.show_error(f"Process no longer exists (pid={powershell_pid})")
                else:
                    children = parent.children(recursive=True)
        #     return  # Esce dalla funzione se il processo non esiste più
        # children = parent.children(recursive=True)
                
                # Termina prima i processi figli (incluso il processo AWS SSM)
                    for child in children:
                        
                        try:
                            child.terminate()
                            child.wait(timeout=5)  # Aspetta che il processo figlio termini
                        except psutil.NoSuchProcess:
                            logger.warning(f"Child process no longer exists (pid={child.pid})")
                        except psutil.TimeoutExpired:
                            child.kill()  # Forza la chiusura se non termina entro 5 secondi
                
                # Ora termina il processo PowerShell genitore
                #parent.terminate()
                try:
                    parent.terminate()
                    parent.wait(timeout=5)  # Aspetta che il processo PowerShell termini
                except psutil.NoSuchProcess:
                    logger.warning(f"Parent process no longer exists (pid={powershell_pid})")
                except psutil.TimeoutExpired:
                    parent.kill()  # Forza la chiusura se non termina entro 5 secondi

                # **Modifica aggiunta**: Aggiungi un breve ritardo per assicurarti che tutti i processi siano chiusi
                time.sleep(2)  # Attendi 2 secondi per garantire che il processo venga completamente chiuso

                # Chiudi eventuali finestre associate al processo
                def close_window(hwnd, _):
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid == powershell_pid:
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)  # Invia messaggio per chiudere la finestra
                    except:
                        pass  # Ignora eventuali errori durante la chiusura della finestra
                
                win32gui.EnumWindows(close_window, None)
            
            # Rimuovi la connessione dalla lista delle connessioni attive
            if connection in self.active_connections:
                self.active_connections.remove(connection)
            else:
                logger.warning(f"Connection not found in active_connections: {connection}")
                
            self.update_active_connections()
            
            logger.info(f"Connection terminated for instance {connection['instance_id']}")
        
        except Exception as e:
            logger.error(f"Error terminating connection: {str(e)}")
            self.show_error(f"Error terminating connection: {str(e)}")

    # def show_loading(self, message):
    #     self.loading_label.config(text=message)

    # def hide_loading(self):
    #     self.loading_label.config(text="")

    def show_error(self, message):
        Messagebox.show_error(message, "Error", parent=self)

    def load_preferences(self):
        try:
            with open(resource_path('preferences.json'), 'r') as f: #with open('preferences.json', 'r') as f:
                self.preferences = json.load(f)
        except FileNotFoundError:
            self.preferences = {}

        # Initialize profile_var and region_var with values from preferences or defaults
        self.profile_var = ttk.StringVar(value=self.preferences.get('profile', ''))
        self.region_var = ttk.StringVar(value=self.preferences.get('region', ''))

        # Set default log level if not present
        if 'log_level' not in self.preferences:
            self.preferences['log_level'] = 'DEBUG'
            self.save_preferences()
            
        # Update log level
        log_level = getattr(logging, self.preferences['log_level'])
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)

    def save_preferences(self):
        self.preferences.update({
            'profile': self.profile_var.get(),
            'region': self.region_var.get(),
        })
        with open(resource_path('preferences.json'), 'w') as f: #with open('preferences.json', 'w') as f:
            json.dump(self.preferences, f)

    # def on_closing(self):
    #     if Messagebox.yesno("Quit", "Do you want to quit?"):
    #         self.aws_thread.stop()
    #         self.aws_thread.join()
    #         self.destroy()
    def on_closing(self):
        msg_box = Messagebox.yesno("Quit", "Do you want to quit?")
        
        if msg_box == "Yes":
            if self.aws_thread:
                self.aws_thread.stop()
                self.aws_thread.join()
            self.destroy()
        else:
            return
        
        # if Messagebox.yesno("Quit", "Do you want to quit?"):
        #     if self.aws_thread:
        #         self.aws_thread.stop()
        #         self.aws_thread.join()
        #     self.destroy()
        # else:
        #     return  # Non fa nulla se l'utente sceglie NO
        
    # def on_closing(self):
    #     should_quit = Messagebox.yesno("Quit", "Do you want to quit?")
        
    #     if should_quit:
    #         if self.aws_thread:
    #             self.aws_thread.stop()
    #             self.aws_thread.join()
    #         self.destroy()  # Chiude l'applicazione se l'utente conferma
    #     else:
    #         self.protocol("WM_DELETE_WINDOW", self.on_closing)  # Riassegna il protocollo di chiusura alla funzione stessa
            
    def change_log_level(self, level):
        self.preferences['log_level'] = level
        self.save_preferences()
        log_level = getattr(logging, level)
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)
        logger.info(f"Log level changed to {level}")

    def create_reverse_port_forwarding_button(self):
        # Crea un frame per il pulsante
        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", anchor="w", padx=10, pady=10)

        # Crea il pulsante "Reverse Port Forwarding"
        reverse_port_button = ttk.Button(button_frame, text="Reverse Port Forwarding", command=self.open_reverse_port_popup, bootstyle="primary")
        reverse_port_button.pack(side="left")

    def open_reverse_port_popup(self):
            # Crea la finestra popup
        popup = tk.Toplevel(self)
        popup.title("Reverse Port Forwarding")
        popup.geometry("500x200")  # Imposta una dimensione fissa per la finestra

        # Ottieni le istanze dal Frame invece che dal Treeview
        instances = []
        for frame in self.instances_frame.winfo_children():
            if isinstance(frame, ttk.Frame):
                name = frame.winfo_children()[0].cget("text").split(": ")[1]
                instance_id = frame.winfo_children()[1].cget("text").split(": ")[1]
                instances.append((name, instance_id))

        # Determina la larghezza massima del nome delle istanze
        max_name_length = max(len(f"{name} ({id})") for name, id in instances) if instances else 10

        # Dropdown per selezionare l'istanza
        ttk.Label(popup, text="Instance:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        instance_var = ttk.StringVar()
        instance_menu = ttk.Combobox(popup, textvariable=instance_var, state="readonly", width=max_name_length)
        instance_menu['values'] = [f"{name} ({id})" for name, id in instances]
        instance_menu.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Campo per l'host remoto
        ttk.Label(popup, text="Remote Host:").grid(row=1, column=0, padx=10, pady=5, sticky="w")  # Allineato a sinistra
        remote_host_var = ttk.StringVar()
        remote_host_entry = ttk.Entry(popup, textvariable=remote_host_var)
        remote_host_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")  # Allineato a sinistra

        # Campo per la porta remota
        ttk.Label(popup, text="Remote Port:").grid(row=2, column=0, padx=10, pady=5, sticky="w")  # Allineato a sinistra
        remote_port_var = ttk.StringVar()
        remote_port_entry = ttk.Entry(popup, textvariable=remote_port_var)
        remote_port_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")  # Allineato a sinistra

        # Campo per la porta locale
        ttk.Label(popup, text="Local Port:").grid(row=3, column=0, padx=10, pady=5, sticky="w")  # Allineato a sinistra
        local_port_var = ttk.StringVar()
        local_port_entry = ttk.Entry(popup, textvariable=local_port_var)
        local_port_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")  # Allineato a sinistra

        # Bottone di connessione
        connect_button = ttk.Button(popup, text="Connetti", command=lambda: print("Connection logic here"))
        connect_button.grid(row=4, column=0, columnspan=2, pady=10)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = AWSSSMManagerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()