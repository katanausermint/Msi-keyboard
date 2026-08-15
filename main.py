#!/usr/bin/env python3
"""
MSI Keyboard RGB Controller - ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ
Правильный протокол: байт 10 = 0x00, затем R, G, B, яркость
"""

import os
import sys
import subprocess
import usb.core
import usb.util
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import json
import time
from typing import Dict, Tuple, Optional

# ============== ПРОВЕРКА ПРАВ ==============
def check_and_request_permissions():
    if os.geteuid() != 0:
        print("Требуются права root. Перезапуск с sudo...")
        try:
            env = os.environ.copy()
            subprocess.run(['sudo', '-E', 'python3', __file__], env=env)
            sys.exit(0)
        except Exception as e:
            print(f"Ошибка: {e}")
            sys.exit(1)

# ============== КОНФИГУРАЦИЯ ==============
VENDOR_ID = 0x1462
PRODUCT_ID = 0x1601
INTERFACE = 0
REPORT_ID_SEND = 2
REPORT_ID_RECV = 1
TIMEOUT = 1000

ZONES = {
    'Вся клавиатура': 0x0F,
    'Зона 1': 0x01,
    'Зона 2': 0x02,
    'Зона 3': 0x04,
    'Зона 4': 0x08,
}

ANIMATION_TYPES = {
    'Статичный': 0x01,
    'Дыхание': 0x02,
    'Волна': 0x03,
    'Реактивный': 0x04,
    'Радуга': 0x05,
    'Градиент': 0x06,
}

SPEEDS = {
    'Очень медленно': 0x0100,
    'Медленно': 0x0200,
    'Средне': 0x0300,
    'Быстро': 0x0400,
    'Очень быстро': 0x0500,
}

BRIGHTNESS_LEVELS = {
    'Выкл': 0x00,
    'Низкая': 0x33,
    'Средняя': 0x66,
    'Высокая': 0x99,
    'Максимальная': 0xFF,
}

THEME = {
    'bg_dark': '#1a1a1a',
    'bg_medium': '#2d2d2d',
    'bg_light': '#3d3d3d',
    'accent': '#ff4444',
    'text': '#ffffff',
    'text_secondary': '#b0b0b0',
    'button': '#4a4a4a',
    'button_hover': '#5a5a5a',
}

# ============== USB КОНТРОЛЛЕР ==============
class USBController:
    """Контроллер USB с правильным протоколом"""
    
    def __init__(self):
        self.device = None
        self.connected = False
    
    def connect(self) -> bool:
        """Подключение к устройству"""
        try:
            self.device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
            if self.device is None:
                print("Устройство не найдено")
                return False
            
            if self.device.is_kernel_driver_active(INTERFACE):
                try:
                    self.device.detach_kernel_driver(INTERFACE)
                except:
                    pass
            
            try:
                self.device.set_configuration()
            except:
                pass
            
            self.connected = True
            print("✓ Устройство подключено")
            return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False
    
    def disconnect(self):
        """Отключение от устройства"""
        if self.device:
            try:
                usb.util.release_interface(self.device, INTERFACE)
                try:
                    self.device.attach_kernel_driver(INTERFACE)
                except:
                    pass
                self.connected = False
                self.device = None
                print("Устройство отключено")
            except:
                pass
    
    def _send_feature_report(self, data: bytes) -> bool:
        """Отправка HID Feature Report"""
        if not self.connected:
            return False
        
        try:
            report = bytearray([REPORT_ID_SEND] + list(data))
            report += b'\x00' * (64 - len(report))
            
            self.device.ctrl_transfer(
                bmRequestType=0x21,
                bRequest=0x09,
                wValue=0x0300 | REPORT_ID_SEND,
                wIndex=0,
                data_or_wLength=report,
                timeout=TIMEOUT
            )
            time.sleep(0.1)
            
            self.device.ctrl_transfer(
                bmRequestType=0xA1,
                bRequest=0x01,
                wValue=0x0300 | REPORT_ID_RECV,
                wIndex=0,
                data_or_wLength=64,
                timeout=TIMEOUT
            )
            time.sleep(0.1)
            
            return True
        except Exception as e:
            print(f"Ошибка отправки: {e}")
            return False
    
    def select_zone(self, zone_mask: int) -> bool:
        """Выбор зоны"""
        return self._send_feature_report(bytes([0x01, zone_mask]))
    
    def set_static_color(self, zone_mask: int, red: int, green: int, blue: int, brightness: int = 0xFF) -> bool:
        """Установка статического цвета (ПРАВИЛЬНЫЙ формат)"""
        # Черный = выключить
        if red == 0 and green == 0 and blue == 0:
            brightness = 0x00
        
        data = bytes([
            0x02,       # Packet ID
            0x01,       # Animation Type: Steady
            0x00, 0x00, # Speed
            0x00, 0x00, 0x0F, 0x01,  # Константы
            0x00,       # Direction
            0x00,       # ВАЖНО: всегда 0!
            red, green, blue,  # RGB в правильном порядке
            brightness   # Яркость
        ])
        
        if not self.select_zone(zone_mask):
            return False
        time.sleep(0.1)
        return self._send_feature_report(data)
    
    def set_animation(self, zone_mask: int, anim_type: int, speed: int, red: int, green: int, blue: int, brightness: int = 0xFF) -> bool:
        """Установка анимации (ПРАВИЛЬНЫЙ формат)"""
        data = bytes([
            0x02,       # Packet ID
            anim_type,  # Animation Type
            speed & 0xFF, (speed >> 8) & 0xFF,  # Speed little endian
            0x00, 0x00, 0x0F, 0x01,  # Константы
            0x00,       # Direction
            0x00,       # ВАЖНО: всегда 0!
            red, green, blue,  # RGB в правильном порядке
            brightness   # Яркость
        ])
        
        if not self.select_zone(zone_mask):
            return False
        time.sleep(0.1)
        return self._send_feature_report(data)
    
    def save_to_flash(self) -> bool:
        """Сохранение в flash"""
        return self._send_feature_report(bytes([0xA0]))
    
    def load_from_flash(self) -> bool:
        """Загрузка из flash"""
        return self._send_feature_report(bytes([0xB0]))

# ============== УПРАВЛЕНИЕ ПРЕСЕТАМИ ==============
class PresetManager:
    """Управление пресетами"""
    
    def __init__(self, config_file='keyboard_presets.json'):
        self.config_file = config_file
        self.presets: Dict[str, Dict] = {}
        self.load_presets()
    
    def load_presets(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            except:
                self.presets = {}
        else:
            self.presets = self._get_default_presets()
            self.save_presets()
    
    def save_presets(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def _get_default_presets(self) -> Dict:
        return {
            "Игровой": {"mode": "Реактивный", "color": "#00ff00", "brightness": "Максимальная", "speed": "Быстро", "zone": "Вся клавиатура"},
            "Спокойный": {"mode": "Дыхание", "color": "#0000ff", "brightness": "Средняя", "speed": "Медленно", "zone": "Вся клавиатура"},
            "Радуга": {"mode": "Радуга", "color": "#ffffff", "brightness": "Максимальная", "speed": "Средне", "zone": "Вся клавиатура"},
            "Рабочий": {"mode": "Статичный", "color": "#ffffff", "brightness": "Максимальная", "speed": "Средне", "zone": "Вся клавиатура"}
        }
    
    def get_preset(self, name: str) -> Optional[Dict]:
        return self.presets.get(name)
    
    def save_preset(self, name: str, settings: Dict):
        self.presets[name] = settings
        self.save_presets()
    
    def delete_preset(self, name: str):
        if name in self.presets:
            del self.presets[name]
            self.save_presets()
    
    def get_all_presets(self) -> Dict:
        return self.presets

# ============== ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ==============
class MSIKeyboardGUI:
    """Графический интерфейс"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.usb = USBController()
        self.presets = PresetManager()
        
        self.current_color = "#ff0000"
        self.current_mode = tk.StringVar(value="Статичный")
        self.current_zone = tk.StringVar(value="Вся клавиатура")
        self.current_brightness = tk.StringVar(value="Максимальная")
        self.current_speed = tk.StringVar(value="Средне")
        self.connection_status = tk.StringVar(value="Отключено")
        
        self.setup_window()
        self.create_widgets()
        self.apply_theme()
        self.root.after(1000, self.auto_connect)
    
    def setup_window(self):
        self.root.title("MSI Keyboard RGB Controller")
        self.root.geometry("1000x750")
        self.root.minsize(900, 650)
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 1000) // 2
        y = (screen_height - 750) // 2
        self.root.geometry(f"1000x750+{x}+{y}")
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg=THEME['bg_dark'])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Верхняя панель
        top_panel = tk.Frame(main_frame, bg=THEME['bg_dark'])
        top_panel.pack(fill="x", pady=(0, 20))
        
        tk.Label(top_panel, text="MSI KEYBOARD RGB CONTROLLER", font=("Arial", 24, "bold"), bg=THEME['bg_dark'], fg=THEME['accent']).pack(side="left")
        
        status_frame = tk.Frame(top_panel, bg=THEME['bg_dark'])
        status_frame.pack(side="right")
        
        self.status_dot = tk.Canvas(status_frame, width=15, height=15, bg=THEME['bg_dark'], highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 5))
        
        tk.Label(status_frame, textvariable=self.connection_status, font=("Arial", 12), bg=THEME['bg_dark'], fg=THEME['text']).pack(side="left", padx=(0, 10))
        
        self.connect_button = tk.Button(status_frame, text="Подключить", command=self.toggle_connection, font=("Arial", 11), bg=THEME['button'], fg=THEME['text'], relief="flat", padx=15, pady=5, cursor="hand2")
        self.connect_button.pack(side="left")
        
        # Основная область
        content_frame = tk.Frame(main_frame, bg=THEME['bg_dark'])
        content_frame.pack(fill="both", expand=True)
        
        # Левая панель
        left_panel = tk.Frame(content_frame, bg=THEME['bg_medium'])
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Режим
        mode_frame = tk.LabelFrame(left_panel, text="Режим", font=("Arial", 12, "bold"), bg=THEME['bg_medium'], fg=THEME['accent'], padx=15, pady=10)
        mode_frame.pack(fill="x", padx=10, pady=10)
        
        for mode in ANIMATION_TYPES.keys():
            rb = tk.Radiobutton(mode_frame, text=mode, variable=self.current_mode, value=mode, font=("Arial", 11), bg=THEME['bg_medium'], fg=THEME['text'], selectcolor=THEME['bg_light'], activebackground=THEME['bg_medium'], activeforeground=THEME['accent'], anchor="w", cursor="hand2")
            rb.pack(fill="x", pady=2)
        
        # Зона
        zone_frame = tk.LabelFrame(left_panel, text="Зона", font=("Arial", 12, "bold"), bg=THEME['bg_medium'], fg=THEME['accent'], padx=15, pady=10)
        zone_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Combobox(zone_frame, textvariable=self.current_zone, values=list(ZONES.keys()), state="readonly", font=("Arial", 11)).pack(fill="x", pady=5)
        
        # Яркость
        brightness_frame = tk.LabelFrame(left_panel, text="Яркость", font=("Arial", 12, "bold"), bg=THEME['bg_medium'], fg=THEME['accent'], padx=15, pady=10)
        brightness_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Combobox(brightness_frame, textvariable=self.current_brightness, values=list(BRIGHTNESS_LEVELS.keys()), state="readonly", font=("Arial", 11)).pack(fill="x", pady=5)
        
        # Скорость
        speed_frame = tk.LabelFrame(left_panel, text="Скорость", font=("Arial", 12, "bold"), bg=THEME['bg_medium'], fg=THEME['accent'], padx=15, pady=10)
        speed_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Combobox(speed_frame, textvariable=self.current_speed, values=list(SPEEDS.keys()), state="readonly", font=("Arial", 11)).pack(fill="x", pady=5)
        
        # Центральная панель
        center_panel = tk.Frame(content_frame, bg=THEME['bg_medium'])
        center_panel.pack(side="left", fill="both", expand=True, padx=10)
        
        # Цвет
        color_frame = tk.LabelFrame(center_panel, text="Цвет", font=("Arial", 12, "bold"), bg=THEME['bg_medium'], fg=THEME['accent'], padx=15, pady=10)
        color_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.color_button = tk.Button(color_frame, text="Выбрать цвет", command=self.choose_color, font=("Arial", 12), bg=self.current_color, fg="white" if self._is_dark_color(self.current_color) else "black", relief="flat", padx=20, pady=15, cursor="hand2")
        self.color_button.pack(pady=20)
        
        # RGB слайдеры
        rgb_frame = tk.Frame(color_frame, bg=THEME['bg_medium'])
        rgb_frame.pack(fill="x", pady=10)
        
        tk.Label(rgb_frame, text="R:", font=("Arial", 11), bg=THEME['bg_medium'], fg="#ff4444").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.red_scale = tk.Scale(rgb_frame, from_=0, to=255, orient="horizontal", command=self.on_rgb_change, bg=THEME['bg_medium'], fg="#ff4444", troughcolor="#ff4444", highlightthickness=0)
        self.red_scale.set(255)
        self.red_scale.grid(row=0, column=1, sticky="ew", pady=2)
        
        tk.Label(rgb_frame, text="G:", font=("Arial", 11), bg=THEME['bg_medium'], fg="#44ff44").grid(row=1, column=0, sticky="w", padx=(0, 5))
        self.green_scale = tk.Scale(rgb_frame, from_=0, to=255, orient="horizontal", command=self.on_rgb_change, bg=THEME['bg_medium'], fg="#44ff44", troughcolor="#44ff44", highlightthickness=0)
        self.green_scale.set(0)
        self.green_scale.grid(row=1, column=1, sticky="ew", pady=2)
        
        tk.Label(rgb_frame, text="B:", font=("Arial", 11), bg=THEME['bg_medium'], fg="#4444ff").grid(row=2, column=0, sticky="w", padx=(0, 5))
        self.blue_scale = tk.Scale(rgb_frame, from_=0, to=255, orient="horizontal", command=self.on_rgb_change, bg=THEME['bg_medium'], fg="#4444ff", troughcolor="#4444ff", highlightthickness=0)
        self.blue_scale.set(0)
        self.blue_scale.grid(row=2, column=1, sticky="ew", pady=2)
        
        rgb_frame.grid_columnconfigure(1, weight=1)
        
        # Предпросмотр
        preview_frame = tk.Frame(color_frame, bg=THEME['bg_medium'])
        preview_frame.pack(fill="both", expand=True, pady=10)
        
        self.preview_canvas = tk.Canvas(preview_frame, height=200, bg=THEME['bg_light'], highlightthickness=2, highlightbackground=THEME['accent'])
        self.preview_canvas.pack(fill="both", expand=True)
        
        self.draw_keyboard_preview()
        
        # Правая панель
        right_panel = tk.Frame(content_frame, bg=THEME['bg_medium'])
        right_panel.pack(side="right", fill="both", padx=(10, 0))
        
        preset_frame = tk.LabelFrame(right_panel, text="Пресеты", font=("Arial", 12, "bold"), bg=THEME['bg_medium'], fg=THEME['accent'], padx=15, pady=10)
        preset_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.preset_listbox = tk.Listbox(preset_frame, font=("Arial", 11), bg=THEME['bg_light'], fg=THEME['text'], selectbackground=THEME['accent'], selectforeground="white", relief="flat", height=15)
        self.preset_listbox.pack(fill="both", expand=True, pady=5)
        
        preset_buttons = tk.Frame(preset_frame, bg=THEME['bg_medium'])
        preset_buttons.pack(fill="x", pady=5)
        
        tk.Button(preset_buttons, text="Сохранить", command=self.save_current_preset, font=("Arial", 10), bg=THEME['button'], fg=THEME['text'], relief="flat", cursor="hand2").pack(side="left", expand=True, fill="x", padx=(0, 2))
        tk.Button(preset_buttons, text="Загрузить", command=self.load_selected_preset, font=("Arial", 10), bg=THEME['button'], fg=THEME['text'], relief="flat", cursor="hand2").pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(preset_buttons, text="Удалить", command=self.delete_selected_preset, font=("Arial", 10), bg=THEME['button'], fg=THEME['text'], relief="flat", cursor="hand2").pack(side="left", expand=True, fill="x", padx=(2, 0))
        
        self.update_preset_list()
        
        # Нижняя панель
        bottom_panel = tk.Frame(main_frame, bg=THEME['bg_dark'])
        bottom_panel.pack(fill="x", pady=(20, 0))
        
        tk.Button(bottom_panel, text="Сохранить в Flash", command=self.save_to_flash, font=("Arial", 11), bg=THEME['button'], fg=THEME['text'], relief="flat", padx=15, pady=8, cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(bottom_panel, text="Загрузить из Flash", command=self.load_from_flash, font=("Arial", 11), bg=THEME['button'], fg=THEME['text'], relief="flat", padx=15, pady=8, cursor="hand2").pack(side="left", padx=(0, 10))
        
        tk.Button(bottom_panel, text="Применить", command=self.apply_settings, font=("Arial", 12, "bold"), bg=THEME['accent'], fg="white", relief="flat", padx=20, pady=10, cursor="hand2").pack(side="right")
    
    def apply_theme(self):
        self.root.configure(bg=THEME['bg_dark'])
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground=THEME['bg_light'], background=THEME['button'], foreground=THEME['text'], arrowcolor=THEME['text'])
    
    def update_status_dot(self):
        if self.usb.connected:
            color = "#00ff00"
            self.connection_status.set("Подключено")
            self.connect_button.config(text="Отключить")
        else:
            color = "#ff0000"
            self.connection_status.set("Отключено")
            self.connect_button.config(text="Подключить")
        
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 13, 13, fill=color, outline="")
    
    def auto_connect(self):
        if not self.usb.connected:
            if self.usb.connect():
                print("✓ Устройство подключено")
            self.update_status_dot()
        self.root.after(5000, self.auto_connect)
    
    def toggle_connection(self):
        if self.usb.connected:
            self.usb.disconnect()
        else:
            if self.usb.connect():
                print("✓ Устройство подключено")
            else:
                messagebox.showerror("Ошибка", "Не удалось подключиться")
        self.update_status_dot()
    
    def choose_color(self):
        color = colorchooser.askcolor(color=self.current_color, title="Выберите цвет")
        if color[1]:
            self.current_color = color[1]
            self.update_color_button()
            r, g, b = self._hex_to_rgb(color[1])
            self.red_scale.set(r)
            self.green_scale.set(g)
            self.blue_scale.set(b)
            self.draw_keyboard_preview()
    
    def on_rgb_change(self, event=None):
        r = self.red_scale.get()
        g = self.green_scale.get()
        b = self.blue_scale.get()
        self.current_color = f"#{r:02x}{g:02x}{b:02x}"
        self.update_color_button()
        self.draw_keyboard_preview()
    
    def update_color_button(self):
        self.color_button.config(bg=self.current_color, fg="white" if self._is_dark_color(self.current_color) else "black")
    
    def draw_keyboard_preview(self):
        self.preview_canvas.delete("all")
        width = self.preview_canvas.winfo_width()
        height = self.preview_canvas.winfo_height()
        
        if width < 100:
            width = 400
            height = 200
        
        margin_x = width * 0.1
        margin_y = height * 0.2
        keyboard_width = width * 0.8
        keyboard_height = height * 0.6
        
        self.preview_canvas.create_rectangle(margin_x, margin_y, margin_x + keyboard_width, margin_y + keyboard_height, fill=THEME['bg_light'], outline=THEME['text_secondary'], width=2)
        
        keys_per_row = 15
        rows = 5
        key_spacing = keyboard_width / (keys_per_row + 1)
        row_spacing = keyboard_height / (rows + 1)
        
        for row in range(rows):
            for col in range(keys_per_row):
                x1 = margin_x + key_spacing * (col + 0.8)
                y1 = margin_y + row_spacing * (row + 0.8)
                x2 = x1 + key_spacing * 0.4
                y2 = y1 + row_spacing * 0.4
                
                self.preview_canvas.create_rectangle(x1, y1, x2, y2, fill=self.current_color, outline=THEME['text_secondary'], width=1)
    
    def apply_settings(self):
        if not self.usb.connected:
            messagebox.showwarning("Предупреждение", "Устройство не подключено")
            return
        
        try:
            zone_mask = ZONES[self.current_zone.get()]
            r, g, b = self._hex_to_rgb(self.current_color)
            mode = self.current_mode.get()
            speed = SPEEDS[self.current_speed.get()]
            brightness = BRIGHTNESS_LEVELS[self.current_brightness.get()]
            
            success = False
            
            if mode == "Статичный":
                success = self.usb.set_static_color(zone_mask, r, g, b, brightness)
            else:
                anim_type = ANIMATION_TYPES[mode]
                success = self.usb.set_animation(zone_mask, anim_type, speed, r, g, b, brightness)
            
            if success:
                messagebox.showinfo("Успех", "Настройки применены")
                print("✓ Настройки применены")
            else:
                messagebox.showerror("Ошибка", "Не удалось применить настройки")
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {e}")
            print(f"✗ Ошибка: {e}")
    
    def save_to_flash(self):
        if self.usb.connected and self.usb.save_to_flash():
            messagebox.showinfo("Успех", "Сохранено в flash")
    
    def load_from_flash(self):
        if self.usb.connected and self.usb.load_from_flash():
            messagebox.showinfo("Успех", "Загружено из flash")
    
    def save_current_preset(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Сохранить пресет")
        dialog.geometry("300x150")
        dialog.configure(bg=THEME['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Введите имя пресета:", font=("Arial", 11), bg=THEME['bg_dark'], fg=THEME['text']).pack(pady=10)
        
        entry = tk.Entry(dialog, font=("Arial", 11), bg=THEME['bg_light'], fg=THEME['text'], insertbackground=THEME['text'])
        entry.pack(pady=5, padx=20, fill="x")
        entry.focus()
        
        def save():
            name = entry.get().strip()
            if name:
                settings = {
                    "mode": self.current_mode.get(),
                    "color": self.current_color,
                    "brightness": self.current_brightness.get(),
                    "speed": self.current_speed.get(),
                    "zone": self.current_zone.get()
                }
                self.presets.save_preset(name, settings)
                self.update_preset_list()
                dialog.destroy()
                messagebox.showinfo("Успех", f"Пресет '{name}' сохранен")
        
        tk.Button(dialog, text="Сохранить", command=save, font=("Arial", 11), bg=THEME['accent'], fg="white", relief="flat", padx=20, pady=5, cursor="hand2").pack(pady=10)
        entry.bind("<Return>", lambda e: save())
    
    def load_selected_preset(self):
        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите пресет")
            return
        
        preset_name = self.preset_listbox.get(selection[0])
        preset = self.presets.get_preset(preset_name)
        
        if preset:
            self.current_mode.set(preset.get("mode", "Статичный"))
            self.current_color = preset.get("color", "#ff0000")
            self.current_brightness.set(preset.get("brightness", "Максимальная"))
            self.current_speed.set(preset.get("speed", "Средне"))
            self.current_zone.set(preset.get("zone", "Вся клавиатура"))
            
            self.update_color_button()
            r, g, b = self._hex_to_rgb(self.current_color)
            self.red_scale.set(r)
            self.green_scale.set(g)
            self.blue_scale.set(b)
            self.draw_keyboard_preview()
            
            self.apply_settings()
    
    def delete_selected_preset(self):
        selection = self.preset_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите пресет")
            return
        
        preset_name = self.preset_listbox.get(selection[0])
        
        if messagebox.askyesno("Подтверждение", f"Удалить пресет '{preset_name}'?"):
            self.presets.delete_preset(preset_name)
            self.update_preset_list()
    
    def update_preset_list(self):
        self.preset_listbox.delete(0, tk.END)
        for preset_name in self.presets.get_all_presets().keys():
            self.preset_listbox.insert(tk.END, preset_name)
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _is_dark_color(self, hex_color: str) -> bool:
        r, g, b = self._hex_to_rgb(hex_color)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return brightness < 128
    
    def on_closing(self):
        if self.usb.connected:
            self.usb.disconnect()
        self.root.destroy()

# ============== ГЛАВНАЯ ФУНКЦИЯ ==============
def main():
    check_and_request_permissions()
    
    root = tk.Tk()
    app = MSIKeyboardGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nПриложение остановлено")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        messagebox.showerror("Ошибка", f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()