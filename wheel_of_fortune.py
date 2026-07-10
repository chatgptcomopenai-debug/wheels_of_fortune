"""
╔══════════════════════════════════════════════════════════╗
║               🎰  КОЛЕСО ФОРТУНЫ  🎰                   ║
║           Wheel of Fortune — Desktop App v2              ║
╠══════════════════════════════════════════════════════════╣
║  pip install pygame-ce                                   ║
║  python wheel_of_fortune.py                              ║
╚══════════════════════════════════════════════════════════╝
"""

import pygame
import pygame.gfxdraw
import math
import random
import sys
import time
import json
import os
import hashlib
try:
    import ctypes
except ImportError:
    ctypes = None

import struct

try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

pygame.init()
pygame.mixer.init()

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60
DATA_DIR = os.path.join(os.path.expanduser("~"), ".wheel_of_fortune")
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
WHEELS_DIR = os.path.join(DATA_DIR, "wheels")
os.makedirs(WHEELS_DIR, exist_ok=True)

# ═══════════════════ ЦВЕТОВЫЕ СХЕМЫ ═══════════════════
COLOR_SCHEMES = {
    "Неон": [
        (0,255,200),(255,0,128),(128,0,255),(255,200,0),
        (0,180,255),(255,80,0),(0,255,80),(255,0,255),
        (100,255,0),(255,120,180),(0,200,150),(220,220,0),
    ],
    "Пастель": [
        (129,212,250),(248,187,208),(206,147,216),(255,245,157),
        (128,222,234),(255,204,128),(165,214,167),(244,143,177),
        (220,231,117),(255,171,145),(149,184,209),(255,224,130),
    ],
    "Океан": [
        (0,119,182),(0,150,199),(0,180,216),(72,202,228),
        (144,224,239),(173,232,244),(202,240,248),(0,105,148),
        (3,86,130),(0,65,106),(0,150,170),(100,200,220),
    ],
    "Закат": [
        (255,0,54),(255,65,54),(255,107,53),(255,154,0),
        (255,183,77),(255,213,79),(239,83,80),(211,47,47),
        (244,67,54),(255,138,101),(255,167,38),(251,192,45),
    ],
    "Радуга": [
        (255,0,0),(255,127,0),(255,255,0),(127,255,0),
        (0,255,0),(0,255,127),(0,255,255),(0,127,255),
        (0,0,255),(127,0,255),(255,0,255),(255,0,127),
    ],
    "Лес": [
        (27,94,32),(46,125,50),(56,142,60),(76,175,80),
        (102,187,106),(129,199,132),(165,214,167),(200,230,201),
        (139,195,74),(104,159,56),(85,139,47),(51,105,30),
    ],
    "Космос": [
        (13,0,50),(25,0,82),(50,0,120),(75,0,160),
        (120,0,200),(160,50,255),(200,100,255),(180,0,220),
        (100,200,255),(50,255,200),(255,100,200),(255,200,50),
    ],
}

# ═══════════════════ ТЕМА ═══════════════════
class Theme:
    def __init__(self, dark=True):
        self.dark = dark
        self.apply()

    def apply(self):
        if self.dark:
            self.bg=(18,18,30); self.panel_bg=(30,30,50)
            self.text=(230,230,255); self.text_dim=(130,130,170)
            self.accent=(0,255,200); self.button_bg=(50,50,80)
            self.button_hover=(70,70,110); self.button_text=(255,255,255)
            self.input_bg=(40,40,65); self.input_border=(80,80,120)
            self.slider_track=(60,60,90); self.slider_fill=(0,255,200)
            self.slider_knob=(255,255,255); self.wheel_border=(200,200,255)
            self.hub_color=(50,50,80); self.hub_border=(0,255,200)
            self.arrow_color=(255,60,60); self.winner_bg=(0,0,0,180)
            self.winner_text=(0,255,200); self.sector_text=(0,0,0)
            self.menu_bg=(25,25,45); self.danger=(255,80,80)
        else:
            self.bg=(240,242,248); self.panel_bg=(255,255,255)
            self.text=(30,30,50); self.text_dim=(120,120,140)
            self.accent=(70,130,255); self.button_bg=(70,130,255)
            self.button_hover=(50,110,240); self.button_text=(255,255,255)
            self.input_bg=(245,245,250); self.input_border=(200,200,220)
            self.slider_track=(200,200,220); self.slider_fill=(70,130,255)
            self.slider_knob=(255,255,255); self.wheel_border=(80,80,120)
            self.hub_color=(255,255,255); self.hub_border=(70,130,255)
            self.arrow_color=(220,50,50); self.winner_bg=(255,255,255,200)
            self.winner_text=(70,130,255); self.sector_text=(40,40,60)
            self.menu_bg=(250,250,255); self.danger=(220,50,50)

    def toggle(self):
        self.dark = not self.dark
        self.apply()

# ═══════════════════ МАТЕМАТИКА СЕКТОРОВ ═══════════════════
# Геометрическое убывание: w_i = (0.5^strength)^i
# strength=0 → все равны, strength=1 → каждый в 2× меньше
def compute_sector_angles(n, strength):
    if n == 0: return []
    if n == 1: return [360.0]
    ratio = 0.5 ** strength
    weights = [ratio ** i for i in range(n)]
    total = sum(weights)
    return [(w / total) * 360.0 for w in weights]

# ═══════════════════ ЗВУКИ ═══════════════════
def _make_buf(samples):
    buf = bytearray(len(samples) * 4)
    for i, val in enumerate(samples):
        val = max(-32768, min(32767, int(val)))
        low = val & 0xFF; high = (val >> 8) & 0xFF
        idx = i * 4
        buf[idx]=low; buf[idx+1]=high; buf[idx+2]=low; buf[idx+3]=high
    return bytes(buf)

def gen_tick_click():
    sr=44100; n=int(sr*0.02)
    s=[16000*math.sin(2*math.pi*800*i/sr)*(1-i/n) for i in range(n)]
    snd=pygame.mixer.Sound(buffer=_make_buf(s)); snd.set_volume(0.25); return snd

def gen_tick_beep():
    sr=44100; n=int(sr*0.03)
    s=[12000*math.sin(2*math.pi*1200*i/sr)*(1-i/n) for i in range(n)]
    snd=pygame.mixer.Sound(buffer=_make_buf(s)); snd.set_volume(0.25); return snd

def gen_tick_soft():
    sr=44100; n=int(sr*0.04)
    s=[8000*math.sin(2*math.pi*400*i/sr)*(1-i/n)**2 for i in range(n)]
    snd=pygame.mixer.Sound(buffer=_make_buf(s)); snd.set_volume(0.3); return snd

def gen_tick_drum():
    sr=44100; n=int(sr*0.05)
    s=[14000*math.sin(2*math.pi*(200-150*i/n)*i/sr)*(1-i/n) for i in range(n)]
    snd=pygame.mixer.Sound(buffer=_make_buf(s)); snd.set_volume(0.3); return snd

def gen_tick_coin():
    sr=44100; n=int(sr*0.06)
    s=[10000*(math.sin(2*math.pi*2000*i/sr)+0.5*math.sin(2*math.pi*3000*i/sr))*(1-i/n)**1.5 for i in range(n)]
    snd=pygame.mixer.Sound(buffer=_make_buf(s)); snd.set_volume(0.2); return snd

def gen_win_sound():
    sr=44100; n=int(sr*0.5)
    s=[8000*max(0,1-i/(n))*(math.sin(2*math.pi*523*i/sr)+math.sin(2*math.pi*659*i/sr)+math.sin(2*math.pi*784*i/sr)) for i in range(n)]
    snd=pygame.mixer.Sound(buffer=_make_buf(s)); snd.set_volume(0.5); return snd

TICK_SOUNDS_INFO = [
    ("Клик", gen_tick_click),
    ("Бип", gen_tick_beep),
    ("Мягкий", gen_tick_soft),
    ("Барабан", gen_tick_drum),
    ("Монетка", gen_tick_coin),
]

# ═══════════════════ КОНФЕТТИ ═══════════════════
class Particle:
    def __init__(self, x, y):
        self.x=x; self.y=y
        a=random.uniform(0,2*math.pi); sp=random.uniform(3,10)
        self.vx=math.cos(a)*sp; self.vy=math.sin(a)*sp-random.uniform(2,6)
        self.gravity=0.15; self.life=random.uniform(1.5,3.0); self.age=0
        self.size=random.randint(3,8); self.rotation=random.uniform(0,360)
        self.rot_speed=random.uniform(-10,10)
        self.color=(random.randint(100,255),random.randint(100,255),random.randint(100,255))

    def update(self,dt):
        self.x+=self.vx; self.vy+=self.gravity; self.y+=self.vy
        self.vx*=0.99; self.age+=dt; self.rotation+=self.rot_speed

    def draw(self,surface):
        alpha=max(0,1.0-self.age/self.life)
        c=(int(self.color[0]*alpha),int(self.color[1]*alpha),int(self.color[2]*alpha))
        r=pygame.Rect(0,0,self.size,int(self.size*0.6)); r.center=(int(self.x),int(self.y))
        s=pygame.Surface((r.w,r.h),pygame.SRCALPHA)
        s.fill((*c,int(255*alpha)))
        rot=pygame.transform.rotate(s,self.rotation)
        surface.blit(rot,rot.get_rect(center=r.center))

    @property
    def alive(self): return self.age < self.life

class ConfettiSystem:
    def __init__(self): self.particles=[]
    def emit(self,x,y,count=100):
        for _ in range(count): self.particles.append(Particle(x,y))
    def update(self,dt):
        for p in self.particles: p.update(dt)
        self.particles=[p for p in self.particles if p.alive]
    def draw(self,surface):
        for p in self.particles: p.draw(surface)

# ═══════════════════ УТИЛИТЫ ═══════════════════
def draw_rounded_rect(surface, color, rect, radius=10):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_text_centered(surface, text, font, color, center):
    r = font.render(text, True, color)
    surface.blit(r, r.get_rect(center=center))

def draw_text_left(surface, text, font, color, pos):
    surface.blit(font.render(text, True, color), pos)

def draw_pie_sector(surface, center, radius, start_deg, end_deg, color):
    cx,cy=center; pts=[(cx,cy)]
    span=end_deg-start_deg; n_pts=max(3,int(abs(span)/2))
    for i in range(n_pts+1):
        a=math.radians(start_deg+(span*i/n_pts))
        pts.append((cx+radius*math.cos(a), cy+radius*math.sin(a)))
    if len(pts)>=3:
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, color, pts, 2)

def get_clipboard():
    if not ctypes: return ""
    try:
        CF=13; u32=ctypes.windll.user32; k32=ctypes.windll.kernel32
        u32.OpenClipboard.argtypes=[ctypes.c_void_p]
        u32.OpenClipboard.restype=ctypes.c_int
        u32.GetClipboardData.argtypes=[ctypes.c_uint]
        u32.GetClipboardData.restype=ctypes.c_void_p
        u32.CloseClipboard.argtypes=[]
        k32.GlobalLock.argtypes=[ctypes.c_void_p]
        k32.GlobalLock.restype=ctypes.c_wchar_p
        k32.GlobalUnlock.argtypes=[ctypes.c_void_p]
        if not u32.OpenClipboard(None): return ""
        try:
            h=u32.GetClipboardData(CF)
            if not h: return ""
            p=k32.GlobalLock(h); r=str(p) if p else ""
            k32.GlobalUnlock(h); return r
        finally: u32.CloseClipboard()
    except: return ""

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ═══════════════════ ПОЛЬЗОВАТЕЛИ ═══════════════════
class UserManager:
    def __init__(self):
        self.users = {}
        self.current_user = None
        self._load()

    def _load(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
            except: self.users = {}

    def _save(self):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)

    def register(self, email, password):
        email = email.strip().lower()
        if not email or "@" not in email: return "Некорректный email"
        if len(password) < 4: return "Пароль мин. 4 символа"
        if email in self.users: return "Email уже занят"
        self.users[email] = {"password": hash_pw(password), "settings": {
            "theme_dark": True, "color_scheme": "Неон", "tick_sound": 0,
            "custom_sound_path": ""
        }}
        self._save()
        self.current_user = email
        return None

    def login(self, email, password):
        email = email.strip().lower()
        if email not in self.users: return "Пользователь не найден"
        if self.users[email]["password"] != hash_pw(password):
            return "Неверный пароль"
        self.current_user = email
        return None

    def logout(self):
        self.current_user = None

    def get_settings(self):
        if self.current_user and self.current_user in self.users:
            return self.users[self.current_user].get("settings", {})
        return {}

    def save_settings(self, settings):
        if self.current_user and self.current_user in self.users:
            self.users[self.current_user]["settings"] = settings
            self._save()

    def get_wheels_dir(self):
        if self.current_user:
            d = os.path.join(WHEELS_DIR, self.current_user.replace("@","_at_"))
            os.makedirs(d, exist_ok=True)
            return d
        return WHEELS_DIR

    def save_wheel(self, name, sectors, scheme, strength):
        d = self.get_wheels_dir()
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)[:50]
        path = os.path.join(d, f"{safe}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"name":name,"sectors":sectors,"scheme":scheme,"strength":strength}, f, ensure_ascii=False, indent=2)

    def list_wheels(self):
        d = self.get_wheels_dir()
        wheels = []
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(d,fn),"r",encoding="utf-8") as f:
                        wheels.append(json.load(f))
                except: pass
        return wheels

    def delete_wheel(self, name):
        d = self.get_wheels_dir()
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)[:50]
        path = os.path.join(d, f"{safe}.json")
        if os.path.exists(path): os.remove(path)

# ═══════════════════ ГЛАВНОЕ ПРИЛОЖЕНИЕ ═══════════════════
class WheelOfFortune:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("🎰 Колесо Фортуны")
        self.clock = pygame.time.Clock()
        self.theme = Theme(dark=True)
        self.user_mgr = UserManager()

        # Шрифты
        self.f_sm = pygame.font.SysFont("segoeui", 16)
        self.f_md = pygame.font.SysFont("segoeui", 20, bold=True)
        self.f_lg = pygame.font.SysFont("segoeui", 32, bold=True)
        self.f_xl = pygame.font.SysFont("segoeui", 48, bold=True)
        self.f_sec = pygame.font.SysFont("segoeui", 14, bold=True)
        self.f_icon = pygame.font.SysFont("segoeui", 22)
        self.f_title = pygame.font.SysFont("segoeui", 28, bold=True)

        # Экран: "login", "register", "main"
        self.screen_mode = "login"
        self.auth_fields = {"email": "", "password": "", "focus": "email", "error": ""}

        # Колесо
        self.sectors = ["Python","JavaScript","Rust","Go","C++","Java","Kotlin","Swift"]
        self.angle = 0.0; self.angular_vel = 0.0; self.spinning = False
        self.friction = 0.985; self.strength = 0.0
        self.winner = None; self.winner_timer = 0; self.show_winner = False
        self.confetti = ConfettiSystem()
        self.last_sector_index = -1

        # Ввод
        self.input_lines = [""]; self.input_cursor_line = 0
        self.input_cursor_col = 0; self.input_active = False
        self.scroll_offset = 0

        # Цветовая схема
        self.color_scheme_name = "Неон"

        # Звуки
        self.tick_sounds = [fn() for _, fn in TICK_SOUNDS_INFO]
        self.tick_sound_idx = 0
        self.custom_sound = None
        self.custom_sound_path = ""
        self.win_sound = gen_win_sound()

        # Меню
        self.menu_open = False
        self.menu_page = "main"  # "main", "wheels", "settings", "colors"
        self.menu_anim = 0.0  # 0=закрыто, 1=открыто
        self.MENU_W = 320

        # Сохранение — имя колеса
        self.save_name = ""
        self.save_name_active = False

        # Колесо и UI ректы
        self.wheel_center = (0,0); self.wheel_radius = 0
        self.slider_rect = pygame.Rect(0,0,0,0)
        self.slider_dragging = False
        self.spin_button_rect = pygame.Rect(0,0,0,0)
        self.add_button_rect = pygame.Rect(0,0,0,0)
        self.input_rect = pygame.Rect(0,0,0,0)
        self.delete_buttons = []
        self._update_layout()

    @property
    def current_tick(self):
        if self.custom_sound: return self.custom_sound
        return self.tick_sounds[self.tick_sound_idx % len(self.tick_sounds)]

    def _update_layout(self):
        w,h = self.screen.get_size()
        wheel_area_w = int(w * 0.62)
        self.wheel_center = (wheel_area_w // 2, h // 2)
        self.wheel_radius = min(wheel_area_w, h) // 2 - 60

    def _apply_user_settings(self):
        s = self.user_mgr.get_settings()
        if s:
            self.theme.dark = s.get("theme_dark", True); self.theme.apply()
            self.color_scheme_name = s.get("color_scheme", "Неон")
            self.tick_sound_idx = s.get("tick_sound", 0)
            cp = s.get("custom_sound_path", "")
            if cp and os.path.exists(cp):
                try:
                    self.custom_sound = pygame.mixer.Sound(cp)
                    self.custom_sound.set_volume(0.3)
                    self.custom_sound_path = cp
                except: self.custom_sound = None

    def _save_user_settings(self):
        self.user_mgr.save_settings({
            "theme_dark": self.theme.dark,
            "color_scheme": self.color_scheme_name,
            "tick_sound": self.tick_sound_idx,
            "custom_sound_path": self.custom_sound_path,
        })

    @property
    def sector_colors(self):
        return COLOR_SCHEMES.get(self.color_scheme_name, COLOR_SCHEMES["Неон"])

    # ═══════════════ СОБЫТИЯ ═══════════════
    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return False
            if ev.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((ev.w,ev.h), pygame.RESIZABLE)
                self._update_layout()

            if self.screen_mode in ("login","register"):
                self._handle_auth_event(ev)
            else:
                self._handle_main_event(ev)
        return True

    # ───── Авторизация ─────
    def _handle_auth_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            f = self.auth_fields
            field = f["focus"]
            if ev.key == pygame.K_TAB:
                f["focus"] = "password" if field == "email" else "email"
            elif ev.key == pygame.K_RETURN:
                self._do_auth()
            elif ev.key == pygame.K_BACKSPACE:
                f[field] = f[field][:-1]
            elif ev.key == pygame.K_v and (ev.mod & pygame.KMOD_CTRL):
                txt = get_clipboard().strip().replace("\n","").replace("\r","")
                f[field] += txt[:50]
            else:
                ch = ev.unicode
                if ch and ch.isprintable() and len(f[field]) < 50:
                    f[field] += ch

        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx,my = ev.pos
            w,h = self.screen.get_size()
            cx = w//2; bw = 340
            # Проверяем поля
            ey = h//2 - 40; py = h//2 + 30
            er = pygame.Rect(cx-bw//2, ey, bw, 36)
            pr = pygame.Rect(cx-bw//2, py, bw, 36)
            if er.collidepoint(mx,my): self.auth_fields["focus"]="email"
            elif pr.collidepoint(mx,my): self.auth_fields["focus"]="password"
            # Кнопка входа/регистрации
            br = pygame.Rect(cx-bw//2, py+55, bw, 44)
            if br.collidepoint(mx,my): self._do_auth()
            # Переключение режима
            sr = pygame.Rect(cx-bw//2, py+110, bw, 30)
            if sr.collidepoint(mx,my):
                self.screen_mode = "register" if self.screen_mode=="login" else "login"
                self.auth_fields["error"] = ""
            # Гостевой вход
            gr = pygame.Rect(cx-bw//2, py+150, bw, 30)
            if gr.collidepoint(mx,my):
                self.screen_mode = "main"

    def _do_auth(self):
        f = self.auth_fields
        if self.screen_mode == "login":
            err = self.user_mgr.login(f["email"], f["password"])
        else:
            err = self.user_mgr.register(f["email"], f["password"])
        if err:
            f["error"] = err
        else:
            f["error"] = ""
            self._apply_user_settings()
            self.screen_mode = "main"

    # ───── Основной экран ─────
    def _handle_main_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if self.menu_open:
                self._handle_menu_key(ev)
                return
            if ev.key == pygame.K_t and not self.input_active and not self.save_name_active:
                self.theme.toggle(); self._save_user_settings()
            elif ev.key == pygame.K_SPACE and not self.input_active and not self.save_name_active:
                self._start_spin()
            elif self.save_name_active:
                self._handle_save_name_key(ev)
            elif self.input_active:
                self._handle_input_key(ev)

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            mx,my = ev.pos
            if ev.button == 1:
                if self.menu_open:
                    self._handle_menu_click(mx,my)
                    return
                # Гамбургер
                if pygame.Rect(10,10,40,40).collidepoint(mx,my):
                    self.menu_open=True; self.menu_page="main"; return
                if self.spin_button_rect.collidepoint(mx,my): self._start_spin()
                elif self.add_button_rect.collidepoint(mx,my): self._add_sectors()
                elif self.input_rect.collidepoint(mx,my):
                    self.input_active=True; self.save_name_active=False
                elif hasattr(self,'save_name_rect') and self.save_name_rect.collidepoint(mx,my):
                    self.save_name_active=True; self.input_active=False
                elif hasattr(self,'save_btn_rect') and self.save_btn_rect.collidepoint(mx,my):
                    self._do_save_wheel()
                else:
                    self.input_active=False; self.save_name_active=False
                    for rect,idx in self.delete_buttons:
                        if rect.collidepoint(mx,my) and len(self.sectors)>2:
                            self.sectors.pop(idx); break
                if self.slider_rect.collidepoint(mx,my):
                    self.slider_dragging=True; self._update_slider(mx)
            elif ev.button==4:
                self.strength=min(1.0,self.strength+0.05)
            elif ev.button==5:
                self.strength=max(0.0,self.strength-0.05)

        elif ev.type == pygame.MOUSEBUTTONUP:
            if ev.button==1: self.slider_dragging=False
        elif ev.type == pygame.MOUSEMOTION:
            if self.slider_dragging: self._update_slider(ev.pos[0])

    def _handle_input_key(self, ev):
        ctrl = ev.mod & pygame.KMOD_CTRL
        if ctrl and ev.key == pygame.K_v:
            self._paste_clipboard()
        elif ctrl and ev.key == pygame.K_a:
            self.input_lines=[""]; self.input_cursor_line=0; self.input_cursor_col=0
        elif ev.key==pygame.K_RETURN:
            if len(self.input_lines)<20:
                l=self.input_lines[self.input_cursor_line]
                self.input_lines[self.input_cursor_line]=l[:self.input_cursor_col]
                self.input_lines.insert(self.input_cursor_line+1,l[self.input_cursor_col:])
                self.input_cursor_line+=1; self.input_cursor_col=0
        elif ev.key==pygame.K_BACKSPACE:
            if self.input_cursor_col>0:
                l=self.input_lines[self.input_cursor_line]
                self.input_lines[self.input_cursor_line]=l[:self.input_cursor_col-1]+l[self.input_cursor_col:]
                self.input_cursor_col-=1
            elif self.input_cursor_line>0:
                prev=self.input_lines[self.input_cursor_line-1]
                cur=self.input_lines.pop(self.input_cursor_line)
                self.input_cursor_line-=1; self.input_cursor_col=len(prev)
                self.input_lines[self.input_cursor_line]=prev+cur
        elif ev.key==pygame.K_UP and self.input_cursor_line>0:
            self.input_cursor_line-=1
            self.input_cursor_col=min(self.input_cursor_col,len(self.input_lines[self.input_cursor_line]))
        elif ev.key==pygame.K_DOWN and self.input_cursor_line<len(self.input_lines)-1:
            self.input_cursor_line+=1
            self.input_cursor_col=min(self.input_cursor_col,len(self.input_lines[self.input_cursor_line]))
        elif ev.key==pygame.K_LEFT and self.input_cursor_col>0:
            self.input_cursor_col-=1
        elif ev.key==pygame.K_RIGHT:
            if self.input_cursor_col<len(self.input_lines[self.input_cursor_line]):
                self.input_cursor_col+=1
        elif ev.key==pygame.K_ESCAPE: self.input_active=False
        else:
            ch=ev.unicode
            if ch and ch.isprintable() and len(self.input_lines[self.input_cursor_line])<30:
                l=self.input_lines[self.input_cursor_line]
                self.input_lines[self.input_cursor_line]=l[:self.input_cursor_col]+ch+l[self.input_cursor_col:]
                self.input_cursor_col+=1

    def _handle_save_name_key(self, ev):
        if ev.key==pygame.K_RETURN: self._do_save_wheel()
        elif ev.key==pygame.K_BACKSPACE: self.save_name=self.save_name[:-1]
        elif ev.key==pygame.K_ESCAPE: self.save_name_active=False
        elif ev.key==pygame.K_v and (ev.mod & pygame.KMOD_CTRL):
            self.save_name+=get_clipboard().strip().replace("\n","")[:30]
        else:
            ch=ev.unicode
            if ch and ch.isprintable() and len(self.save_name)<30:
                self.save_name+=ch

    def _handle_menu_key(self, ev):
        if ev.key == pygame.K_ESCAPE:
            if self.menu_page != "main": self.menu_page = "main"
            else: self.menu_open = False

    def _handle_menu_click(self, mx, my):
        # Клик вне меню = закрыть
        mw = int(self.MENU_W * self.menu_anim)
        if mx > mw:
            self.menu_open = False; return

        # Пункты меню
        if self.menu_page == "main":
            items = [("Мои колёса", "wheels"), ("Цвета колеса", "colors"),
                     ("Настройки", "settings"), ("Тема: {}".format("Тёмная" if self.theme.dark else "Светлая"), "toggle_theme")]
            if self.user_mgr.current_user:
                items.append(("Выйти из аккаунта", "logout"))
            for i, (label, action) in enumerate(items):
                btn_y = 80 + i * 50
                btn_r = pygame.Rect(15, btn_y, mw - 30, 42)
                if btn_r.collidepoint(mx, my):
                    if action == "toggle_theme":
                        self.theme.toggle(); self._save_user_settings()
                    elif action == "logout":
                        self.user_mgr.logout()
                        self.screen_mode = "login"
                        self.auth_fields = {"email":"","password":"","focus":"email","error":""}
                        self.menu_open = False
                    else:
                        self.menu_page = action
                    return
        elif self.menu_page == "wheels":
            # Кнопка «Назад»
            if pygame.Rect(15, 80, 80, 36).collidepoint(mx,my):
                self.menu_page = "main"; return
            # Список колёс
            wheels = self.user_mgr.list_wheels()
            for i, w in enumerate(wheels):
                wy = 130 + i * 60
                lr = pygame.Rect(15, wy, mw-80, 50)
                dr = pygame.Rect(mw-60, wy+10, 40, 30)
                if dr.collidepoint(mx,my):
                    self.user_mgr.delete_wheel(w["name"]); return
                if lr.collidepoint(mx,my):
                    self.sectors=w.get("sectors",["A","B"])
                    self.color_scheme_name=w.get("scheme","Неон")
                    self.strength=w.get("strength",0)
                    self.menu_open=False; return
        elif self.menu_page == "colors":
            if pygame.Rect(15,80,80,36).collidepoint(mx,my):
                self.menu_page="main"; return
            names = list(COLOR_SCHEMES.keys())
            for i, name in enumerate(names):
                cr = pygame.Rect(15, 130+i*50, mw-30, 42)
                if cr.collidepoint(mx,my):
                    self.color_scheme_name=name; self._save_user_settings(); return
        elif self.menu_page == "settings":
            if pygame.Rect(15,80,80,36).collidepoint(mx,my):
                self.menu_page="main"; return
            # Звуки
            for i in range(len(TICK_SOUNDS_INFO)):
                sr = pygame.Rect(15, 170+i*42, mw-30, 36)
                if sr.collidepoint(mx,my):
                    self.tick_sound_idx=i; self.custom_sound=None
                    self.custom_sound_path=""
                    self._save_user_settings()
                    self.tick_sounds[i].play(); return
            # Загрузить свой звук (только если доступен Tkinter)
            if HAS_TKINTER:
                load_y = 170 + len(TICK_SOUNDS_INFO)*42 + 20
                lr = pygame.Rect(15, load_y, mw-30, 42)
                if lr.collidepoint(mx,my):
                    self._load_custom_sound(); return

    def _load_custom_sound(self):
        """Открыть диалог выбора .wav файла."""
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(
            title="Выберите звук", filetypes=[("WAV files","*.wav"),("All","*.*")]
        )
        root.destroy()
        if path and os.path.exists(path):
            try:
                self.custom_sound = pygame.mixer.Sound(path)
                self.custom_sound.set_volume(0.3)
                self.custom_sound_path = path
                self._save_user_settings()
                self.custom_sound.play()
            except: pass

    def _paste_clipboard(self):
        text = get_clipboard().strip()
        if not text: return
        lines = [l.strip() for l in text.replace("\r\n","\n").split("\n")]
        lines = [l for l in lines if l]
        for i, line in enumerate(lines):
            if len(self.input_lines)>=20: break
            line=line[:30]
            if i==0:
                cur=self.input_lines[self.input_cursor_line]
                left=cur[:self.input_cursor_col]; right=cur[self.input_cursor_col:]
                self.input_lines[self.input_cursor_line]=left+line
                self.input_cursor_col=len(left+line)
                if right: self.input_lines.insert(self.input_cursor_line+1, right)
            else:
                self.input_cursor_line+=1
                self.input_lines.insert(self.input_cursor_line, line)
                self.input_cursor_col=len(line)

    def _update_slider(self, mx):
        x=self.slider_rect.x; w=self.slider_rect.w
        self.strength=max(0,min(1,(mx-x)/w))

    def _add_sectors(self):
        added=False
        for line in self.input_lines:
            line=line.strip()
            if line and len(self.sectors)<20:
                self.sectors.append(line[:30]); added=True
        if added:
            self.input_lines=[""]; self.input_cursor_line=0; self.input_cursor_col=0

    def _do_save_wheel(self):
        name = self.save_name.strip()
        if not name: name = f"Колесо {len(self.user_mgr.list_wheels())+1}"
        self.user_mgr.save_wheel(name, self.sectors, self.color_scheme_name, self.strength)
        self.save_name = ""
        self.save_name_active = False

    def _start_spin(self):
        if self.spinning or len(self.sectors)<2: return
        self.spinning=True; self.winner=None; self.show_winner=False
        self.angular_vel=random.uniform(15,30); self.last_sector_index=-1

    # ═══════════════ ОБНОВЛЕНИЕ ═══════════════
    def update(self, dt):
        # Анимация меню
        if self.menu_open: self.menu_anim=min(1.0, self.menu_anim+dt*5)
        else: self.menu_anim=max(0.0, self.menu_anim-dt*5)

        if self.spinning:
            self.angle=(self.angle+self.angular_vel)%360
            angles=compute_sector_angles(len(self.sectors),self.strength)
            pa=(360-self.angle)%360; cum=0; cs=0
            for i,a in enumerate(angles):
                cum+=a
                if pa<cum: cs=i; break
            if cs!=self.last_sector_index:
                self.last_sector_index=cs
                if self.angular_vel>0.5: self.current_tick.play()
            self.angular_vel*=self.friction
            if self.angular_vel<2.0: self.angular_vel*=0.97
            if self.angular_vel<0.5: self.angular_vel*=0.95
            if self.angular_vel<0.02:
                self.angular_vel=0; self.spinning=False
                self._determine_winner()

        self.confetti.update(dt)
        if self.show_winner:
            self.winner_timer-=dt
            if self.winner_timer<=0: self.show_winner=False

    def _determine_winner(self):
        angles=compute_sector_angles(len(self.sectors),self.strength)
        pa=(360-self.angle)%360; cum=0
        for i,a in enumerate(angles):
            cum+=a
            if pa<cum: self.winner=self.sectors[i]; break
        else: self.winner=self.sectors[-1]
        self.show_winner=True; self.winner_timer=5.0
        self.win_sound.play()
        cx,cy=self.wheel_center; r=self.wheel_radius
        self.confetti.emit(cx,cy-r,80)
        self.confetti.emit(cx-60,cy-r+20,50)
        self.confetti.emit(cx+60,cy-r+20,50)

    # ═══════════════ ОТРИСОВКА ═══════════════
    def draw(self):
        if self.screen_mode in ("login","register"):
            self._draw_auth(); pygame.display.flip(); return

        w,h=self.screen.get_size()
        self.screen.fill(self.theme.bg)
        self._draw_hamburger()
        self._draw_wheel()
        self._draw_pointer()
        self._draw_panel(w,h)
        self.confetti.draw(self.screen)
        if self.show_winner and self.winner: self._draw_winner(w,h)
        if self.menu_anim>0.01: self._draw_menu(w,h)
        pygame.display.flip()

    # ───── Авторизация ─────
    def _draw_auth(self):
        w,h=self.screen.get_size()
        self.screen.fill(self.theme.bg)
        cx=w//2; bw=340
        # Заголовок
        title = "Вход" if self.screen_mode=="login" else "Регистрация"
        draw_text_centered(self.screen, "🎰 Колесо Фортуны", self.f_title, self.theme.accent, (cx,h//2-140))
        draw_text_centered(self.screen, title, self.f_lg, self.theme.text, (cx,h//2-90))

        f=self.auth_fields
        # Email
        ey=h//2-40
        er=pygame.Rect(cx-bw//2,ey,bw,36)
        bc=self.theme.accent if f["focus"]=="email" else self.theme.input_border
        draw_rounded_rect(self.screen, self.theme.input_bg, er, 8)
        pygame.draw.rect(self.screen, bc, er, 2, border_radius=8)
        et=f["email"] if f["email"] else "Email..."
        ec=self.theme.text if f["email"] else self.theme.text_dim
        draw_text_left(self.screen, et, self.f_sm, ec, (er.x+10,er.y+8))

        # Password
        py_=h//2+30
        pr=pygame.Rect(cx-bw//2,py_,bw,36)
        bc=self.theme.accent if f["focus"]=="password" else self.theme.input_border
        draw_rounded_rect(self.screen, self.theme.input_bg, pr, 8)
        pygame.draw.rect(self.screen, bc, pr, 2, border_radius=8)
        pt="●"*len(f["password"]) if f["password"] else "Пароль..."
        pc=self.theme.text if f["password"] else self.theme.text_dim
        draw_text_left(self.screen, pt, self.f_sm, pc, (pr.x+10,pr.y+8))

        # Кнопка
        br=pygame.Rect(cx-bw//2,py_+55,bw,44)
        draw_rounded_rect(self.screen, self.theme.accent, br, 10)
        bl="Войти" if self.screen_mode=="login" else "Создать аккаунт"
        draw_text_centered(self.screen, bl, self.f_md, (255,255,255), br.center)

        # Переключение
        sw="Нет аккаунта? Регистрация" if self.screen_mode=="login" else "Уже есть аккаунт? Войти"
        draw_text_centered(self.screen, sw, self.f_sm, self.theme.accent, (cx,py_+125))

        # Гостевой
        draw_text_centered(self.screen, "Войти как гость", self.f_sm, self.theme.text_dim, (cx,py_+165))

        # Ошибка
        if f["error"]:
            draw_text_centered(self.screen, f["error"], self.f_sm, self.theme.danger, (cx,py_+200))

        pygame.display.flip()

    # ───── Гамбургер ─────
    def _draw_hamburger(self):
        x,y=15,18
        for i in range(3):
            pygame.draw.rect(self.screen, self.theme.text, (x,y+i*8,24,3), border_radius=1)

    # ───── Колесо ─────
    def _draw_wheel(self):
        cx,cy=self.wheel_center; r=self.wheel_radius
        n=len(self.sectors)
        if n==0: return
        angles=compute_sector_angles(n,self.strength)
        colors=self.sector_colors; start=self.angle
        for i in range(n):
            span=angles[i]; c=colors[i%len(colors)]
            draw_pie_sector(self.screen,(cx,cy),r,start,start+span,c)
            mid=math.radians(start+span/2); tr=r*0.65
            tx=cx+tr*math.cos(mid); ty=cy+tr*math.sin(mid)
            label=self.sectors[i]; label=label[:11]+"…" if len(label)>12 else label
            ts=self.f_sec.render(label,True,self.theme.sector_text)
            rot=pygame.transform.rotate(ts,-(start+span/2))
            self.screen.blit(rot,rot.get_rect(center=(int(tx),int(ty))))
            start+=span
        pygame.draw.circle(self.screen, self.theme.wheel_border,(cx,cy),r,3)
        pygame.draw.circle(self.screen, self.theme.hub_color,(cx,cy),22)
        pygame.draw.circle(self.screen, self.theme.hub_border,(cx,cy),22,3)
        start=self.angle
        for i in range(n):
            ea=math.radians(start)
            pygame.draw.line(self.screen, self.theme.wheel_border,(cx,cy),(cx+r*math.cos(ea),cy+r*math.sin(ea)),2)
            start+=angles[i]

    def _draw_pointer(self):
        cx,cy=self.wheel_center; r=self.wheel_radius
        ty=cy-r-5; c=self.theme.arrow_color
        pts=[(cx,ty),(cx-18,ty-35),(cx+18,ty-35)]
        pygame.draw.polygon(self.screen,c,pts)
        pygame.draw.polygon(self.screen,(255,255,255),pts,2)

    # ───── Правая панель ─────
    def _draw_panel(self, w, h):
        px=int(w*0.64); pw=w-px-20; py_=20; ph=h-40
        pr=pygame.Rect(px,py_,pw,ph)
        draw_rounded_rect(self.screen, self.theme.panel_bg, pr, 16)
        mx,my=pygame.mouse.get_pos()

        # Заголовок
        draw_text_centered(self.screen,"КОЛЕСО ФОРТУНЫ",self.f_md,self.theme.accent,(px+pw//2,py_+30))

        # Поле ввода
        yc=py_+55; iw=pw-30; lh=20
        vl=min(max(len(self.input_lines),1),5)
        ih=max(34,vl*lh+10)
        self.input_rect=pygame.Rect(px+15,yc,iw,ih)
        bc=self.theme.accent if self.input_active else self.theme.input_border
        draw_rounded_rect(self.screen,self.theme.input_bg,self.input_rect,8)
        pygame.draw.rect(self.screen,bc,self.input_rect,2,border_radius=8)
        has=any(l for l in self.input_lines)
        if not has and not self.input_active:
            draw_text_left(self.screen,"Построчно или Ctrl+V...",self.f_sm,self.theme.text_dim,(self.input_rect.x+10,self.input_rect.y+7))
        else:
            cp=self.screen.get_clip(); self.screen.set_clip(self.input_rect)
            for li,line in enumerate(self.input_lines):
                if li>=5: break
                ly=self.input_rect.y+5+li*lh
                if line: draw_text_left(self.screen,line,self.f_sm,self.theme.text,(self.input_rect.x+10,ly))
                if self.input_active and li==self.input_cursor_line and int(time.time()*2)%2:
                    bef=line[:self.input_cursor_col]
                    cx_=self.input_rect.x+10+(self.f_sm.size(bef)[0] if bef else 0)
                    pygame.draw.line(self.screen,self.theme.accent,(cx_,ly),(cx_,ly+lh-2),2)
            self.screen.set_clip(cp)

        # Кнопка добавить
        yc+=ih+5
        ab=pygame.Rect(px+15,yc,pw-30,30)
        self.add_button_rect=ab
        ac=self.theme.button_hover if ab.collidepoint(mx,my) else self.theme.accent
        draw_rounded_rect(self.screen,ac,ab,8)
        draw_text_centered(self.screen,"ДОБАВИТЬ В КОЛЕСО",self.f_sm,(255,255,255),ab.center)

        # Список секторов
        yc+=40
        list_h=ph-yc+py_-200
        lr=pygame.Rect(px+15,yc,pw-30,list_h)
        draw_rounded_rect(self.screen,self.theme.input_bg,lr,8)
        cp=self.screen.get_clip(); self.screen.set_clip(lr)
        self.delete_buttons=[]
        for i,sec in enumerate(self.sectors):
            iy=yc+4+i*30
            if iy<yc-30 or iy>yc+list_h: continue
            c=self.sector_colors[i%len(self.sector_colors)]
            pygame.draw.circle(self.screen,c,(px+30,iy+14),6)
            draw_text_left(self.screen,sec,self.f_sm,self.theme.text,(px+42,iy+3))
            dr=pygame.Rect(px+pw-55,iy+2,24,24)
            dc=(200,60,60) if dr.collidepoint(mx,my) else self.theme.text_dim
            draw_text_centered(self.screen,"×",self.f_sm,dc,dr.center)
            self.delete_buttons.append((dr,i))
        self.screen.set_clip(cp)

        # Сохранить колесо
        yc+=list_h+10
        self.save_name_rect=pygame.Rect(px+15,yc,pw-100,30)
        sbc=self.theme.accent if self.save_name_active else self.theme.input_border
        draw_rounded_rect(self.screen,self.theme.input_bg,self.save_name_rect,6)
        pygame.draw.rect(self.screen,sbc,self.save_name_rect,2,border_radius=6)
        snt=self.save_name if self.save_name else "Имя колеса..."
        snc=self.theme.text if self.save_name else self.theme.text_dim
        draw_text_left(self.screen,snt,self.f_sm,snc,(self.save_name_rect.x+8,self.save_name_rect.y+6))

        self.save_btn_rect=pygame.Rect(px+pw-80,yc,65,30)
        sbc2=self.theme.button_hover if self.save_btn_rect.collidepoint(mx,my) else self.theme.accent
        draw_rounded_rect(self.screen,sbc2,self.save_btn_rect,6)
        draw_text_centered(self.screen,"💾",self.f_sm,(255,255,255),self.save_btn_rect.center)

        # Слайдер
        yc+=40
        draw_text_centered(self.screen,f"Сила эффекта: {self.strength:.0%}",self.f_sm,self.theme.text,(px+pw//2,yc))
        yc+=20
        sl_x=px+30; sl_w=pw-60
        self.slider_rect=pygame.Rect(sl_x,yc,sl_w,16)
        draw_rounded_rect(self.screen,self.theme.slider_track,pygame.Rect(sl_x,yc+5,sl_w,6),3)
        fw=int(sl_w*self.strength)
        draw_rounded_rect(self.screen,self.theme.slider_fill,pygame.Rect(sl_x,yc+5,fw,6),3)
        pygame.draw.circle(self.screen,self.theme.slider_knob,(sl_x+fw,yc+8),9)
        pygame.draw.circle(self.screen,self.theme.slider_fill,(sl_x+fw,yc+8),9,2)

        # Кнопка крутить
        yc+=35
        sb=pygame.Rect(px+30,yc,pw-60,50)
        self.spin_button_rect=sb
        sc=self.theme.text_dim if self.spinning else (self.theme.button_hover if sb.collidepoint(mx,my) else self.theme.accent)
        draw_rounded_rect(self.screen,sc,sb,12)
        sl="ВРАЩАЕТСЯ..." if self.spinning else "🎰 КРУТИТЬ"
        draw_text_centered(self.screen,sl,self.f_lg,(255,255,255) if not self.spinning else (180,180,180),sb.center)

    # ───── Результат ─────
    def _draw_winner(self, w, h):
        ov=pygame.Surface((w,h),pygame.SRCALPHA); ov.fill(self.theme.winner_bg)
        self.screen.blit(ov,(0,0))
        cw=min(500,w-100); ch_=160
        cr=pygame.Rect((w-cw)//2,(h-ch_)//2,cw,ch_)
        draw_rounded_rect(self.screen,self.theme.panel_bg,cr,20)
        pygame.draw.rect(self.screen,self.theme.accent,cr,3,border_radius=20)
        draw_text_centered(self.screen,"🎉 ПОБЕДИТЕЛЬ 🎉",self.f_md,self.theme.text_dim,(w//2,cr.y+40))
        draw_text_centered(self.screen,self.winner,self.f_xl,self.theme.winner_text,(w//2,cr.y+105))

    # ───── Меню (гамбургер) ─────
    def _draw_menu(self, w, h):
        mw=int(self.MENU_W*self.menu_anim)
        if mw<2: return
        # Затемнение
        ov=pygame.Surface((w,h),pygame.SRCALPHA); ov.fill((0,0,0,int(120*self.menu_anim)))
        self.screen.blit(ov,(0,0))
        # Панель
        mr=pygame.Rect(0,0,mw,h)
        draw_rounded_rect(self.screen,self.theme.menu_bg,mr,0)
        pygame.draw.line(self.screen,self.theme.accent,(mw-1,0),(mw-1,h),2)
        mx_,my_=pygame.mouse.get_pos()

        if self.menu_page=="main":
            draw_text_left(self.screen,"☰ Меню",self.f_title,self.theme.accent,(20,25))
            if self.user_mgr.current_user:
                draw_text_left(self.screen,self.user_mgr.current_user,self.f_sm,self.theme.text_dim,(20,58))
            items=[("📂 Мои колёса","wheels"),("🎨 Цвета колеса","colors"),
                   ("⚙ Настройки","settings"),
                   ("🌙 Тема: "+"Тёмная" if self.theme.dark else "☀ Тема: Светлая","toggle_theme")]
            if self.user_mgr.current_user:
                items.append(("🚪 Выйти","logout"))
            for i,(label,_) in enumerate(items):
                by=80+i*50; br=pygame.Rect(15,by,mw-30,42)
                bc=self.theme.button_hover if br.collidepoint(mx_,my_) else self.theme.button_bg
                draw_rounded_rect(self.screen,bc,br,8)
                draw_text_left(self.screen,label,self.f_sm,self.theme.button_text,(br.x+12,br.y+11))

        elif self.menu_page=="wheels":
            draw_text_left(self.screen,"📂 Мои колёса",self.f_title,self.theme.accent,(20,25))
            # Назад
            bb=pygame.Rect(15,80,80,36)
            draw_rounded_rect(self.screen,self.theme.button_bg,bb,8)
            draw_text_centered(self.screen,"← Назад",self.f_sm,self.theme.button_text,bb.center)
            wheels=self.user_mgr.list_wheels()
            if not wheels:
                draw_text_left(self.screen,"Нет сохранённых колёс",self.f_sm,self.theme.text_dim,(20,140))
            for i,wh in enumerate(wheels):
                wy=130+i*60
                wr=pygame.Rect(15,wy,mw-80,50)
                wc=self.theme.button_hover if wr.collidepoint(mx_,my_) else self.theme.button_bg
                draw_rounded_rect(self.screen,wc,wr,8)
                draw_text_left(self.screen,wh.get("name","?"),self.f_md,self.theme.text,(25,wy+5))
                sc=f"{len(wh.get('sectors',[]))} секторов"
                draw_text_left(self.screen,sc,self.f_sm,self.theme.text_dim,(25,wy+28))
                # Удалить
                dr=pygame.Rect(mw-60,wy+10,40,30)
                drc=self.theme.danger if dr.collidepoint(mx_,my_) else self.theme.text_dim
                draw_rounded_rect(self.screen,self.theme.button_bg,dr,6)
                draw_text_centered(self.screen,"🗑",self.f_sm,drc,dr.center)

        elif self.menu_page=="colors":
            draw_text_left(self.screen,"🎨 Цвета колеса",self.f_title,self.theme.accent,(20,25))
            bb=pygame.Rect(15,80,80,36)
            draw_rounded_rect(self.screen,self.theme.button_bg,bb,8)
            draw_text_centered(self.screen,"← Назад",self.f_sm,self.theme.button_text,bb.center)
            names=list(COLOR_SCHEMES.keys())
            for i,name in enumerate(names):
                cy_=130+i*50; cr=pygame.Rect(15,cy_,mw-30,42)
                active = name==self.color_scheme_name
                cc=self.theme.accent if active else (self.theme.button_hover if cr.collidepoint(mx_,my_) else self.theme.button_bg)
                draw_rounded_rect(self.screen,cc,cr,8)
                tc=(255,255,255) if active else self.theme.button_text
                draw_text_left(self.screen,("✓ " if active else "  ")+name,self.f_sm,tc,(cr.x+10,cr.y+11))
                # Миниатюра цветов
                cols=COLOR_SCHEMES[name]
                for j in range(min(6,len(cols))):
                    pygame.draw.circle(self.screen,cols[j],(cr.x+cr.w-90+j*14,cr.y+21),5)

        elif self.menu_page=="settings":
            draw_text_left(self.screen,"⚙ Настройки",self.f_title,self.theme.accent,(20,25))
            bb=pygame.Rect(15,80,80,36)
            draw_rounded_rect(self.screen,self.theme.button_bg,bb,8)
            draw_text_centered(self.screen,"← Назад",self.f_sm,self.theme.button_text,bb.center)

            draw_text_left(self.screen,"Звук вращения:",self.f_md,self.theme.text,(20,130))
            for i,(sname,_) in enumerate(TICK_SOUNDS_INFO):
                sy=170+i*42; sr_=pygame.Rect(15,sy,mw-30,36)
                active=i==self.tick_sound_idx and not self.custom_sound
                sc=self.theme.accent if active else (self.theme.button_hover if sr_.collidepoint(mx_,my_) else self.theme.button_bg)
                draw_rounded_rect(self.screen,sc,sr_,8)
                tc=(255,255,255) if active else self.theme.button_text
                draw_text_left(self.screen,("♪ " if active else "  ")+sname,self.f_sm,tc,(sr_.x+10,sr_.y+8))

            if HAS_TKINTER:
                load_y=170+len(TICK_SOUNDS_INFO)*42+20
                lr=pygame.Rect(15,load_y,mw-30,42)
                active=bool(self.custom_sound)
                lc=self.theme.accent if active else (self.theme.button_hover if lr.collidepoint(mx_,my_) else self.theme.button_bg)
                draw_rounded_rect(self.screen,lc,lr,8)
                lt="♪ Свой: "+os.path.basename(self.custom_sound_path)[:15] if self.custom_sound_path else "📁 Загрузить свой звук (.wav)"
                tc=(255,255,255) if active else self.theme.button_text
                draw_text_left(self.screen,lt,self.f_sm,tc,(lr.x+10,lr.y+11))

    # ═══════════════ ЦИКЛ ═══════════════
    def run(self):
        running=True
        while running:
            dt=self.clock.tick(FPS)/1000.0
            running=self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit(); sys.exit()

if __name__ == "__main__":
    WheelOfFortune().run()
