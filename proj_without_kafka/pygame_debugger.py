"""
Microservices Real-Time Request Debugger — PREMIUM EDITION (Sync)
=================================================================
A high-fidelity teaching tool visualizing synchronous microservice flows.

Features:
- Deep Space Aesthetic: Radial gradients and particle effects.
- Glassmorphism: Frosted glass nodes with neon glows.
- Sequential Layout: Logical linear progression from User to Service C.
- Organic Animations: Breath-like pulsing and fluid request/response trails.
"""
import pygame
import socket
import json
import threading
import sys
import math
import requests
import time
import subprocess
import signal
from dataclasses import dataclass, field
from typing import List, Tuple

pygame.init()

# ─────────────────────────────────────────────
#  CONSTANTS & LAYOUT
# ─────────────────────────────────────────────
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
LOG_W         = 340
MAIN_W        = WIDTH - LOG_W
NODE_AREA_H   = 600
CTRL_H        = 80
INPUT_H       = HEIGHT - NODE_AREA_H - CTRL_H

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Microservices Debugger — Premium Edition")

# ─────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────
COLOR_BG_DEEP     = (8, 10, 15)
COLOR_BG_MID      = (15, 20, 30)
COLOR_GLASS_BASE  = (25, 30, 45, 160)
COLOR_GLASS_BDR   = (70, 80, 110)
COLOR_NEON_BLUE   = (0, 180, 255)
COLOR_NEON_GREEN  = (50, 255, 130)
COLOR_NEON_RED    = (255, 60, 80)
COLOR_NEON_PURPLE = (180, 100, 255)
COLOR_NEON_YELLOW = (255, 210, 60)

WHITE  = (250, 250, 250)
GRAY   = (120, 130, 150)
L_GRAY = (180, 190, 210)

# ─────────────────────────────────────────────
#  FONTS
# ─────────────────────────────────────────────
F_TITLE = pygame.font.SysFont("Inter, Roboto, sans-serif", 34, bold=True)
F_NODE  = pygame.font.SysFont("Inter, Roboto, sans-serif", 24, bold=True)
F_BODY  = pygame.font.SysFont("Inter, Roboto, sans-serif", 20)
F_SM    = pygame.font.SysFont("Inter, Roboto, sans-serif", 16)
F_TINY  = pygame.font.SysFont("Monospace", 14)

# ─────────────────────────────────────────────
#  SEQUENTIAL LAYOUT
# ─────────────────────────────────────────────
NY = NODE_AREA_H // 2 + 40
NODES = {
    "USER":      (int(MAIN_W * 0.10), NY),
    "Service_A": (int(MAIN_W * 0.36), NY),
    "Service_B": (int(MAIN_W * 0.63), NY),
    "Service_C": (int(MAIN_W * 0.90), NY),
}
NW, NH = 160, 100

NODE_DESC = {
    "USER":      "Client Interface\nInitiates the synchronous flow.",
    "Service_A": "Gateway Service\nValidates requests and\nforwards to Service B.",
    "Service_B": "Sentiment Analyser\nProcesses text and updates\nthe local database.",
    "Service_C": "Dashboard Counter\nReceives metrics and\nbroadcasts via SocketIO.",
}
NODE_PORTS = {"Service_A": "5000", "Service_B": "5002", "Service_C": "5003"}

# ─────────────────────────────────────────────
#  ANIMATION CLASSES
# ─────────────────────────────────────────────
class Ripple:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.radius = 0
        self.alpha = 255
        self.alive = True

    def update(self):
        self.radius += 3
        self.alpha -= 5
        if self.alpha <= 0:
            self.alive = False

    def draw(self, surf):
        s = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, self.alpha), (self.radius, self.radius), self.radius, 2)
        surf.blit(s, (self.x - self.radius, self.y - self.radius))

class Popup:
    def __init__(self, x, y, text, color, duration=2.0):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = duration
        self.alive = True
        self.dy = -1.0

    def update(self):
        self.life -= 0.02
        self.y += self.dy
        if self.life <= 0: self.alive = False

    def draw(self, surf):
        alpha = int(min(255, self.life * 255))
        st = F_SM.render(self.text, True, (*self.color, alpha))
        surf.blit(st, (self.x - st.get_width()//2, self.y))

def draw_dashed_line(surf, color, start_pos, end_pos, width=1, dash_length=10):
    origin = pygame.Vector2(start_pos)
    target = pygame.Vector2(end_pos)
    length = origin.distance_to(target)
    if length == 0: return
    slope = (target - origin) / length
    for index in range(0, int(length), dash_length * 2):
        start = origin + slope * index
        end = origin + slope * min(index + dash_length, length)
        pygame.draw.line(surf, color, start, end, width)

# ─────────────────────────────────────────────
#  SHARED STATE
# ─────────────────────────────────────────────
lock = threading.Lock()
node_status   = {k: "IDLE" for k in NODES}
active_module = {k: ""     for k in NODES}
active_req_id = {k: ""     for k in NODES}
packets: list = []
ripples: list = []
svc_states = {k: True for k in NODES if k != "USER"}
popups: list = []
event_log: list = []
emotion_counts = {"Happy": 0, "Sad": 0, "Angry": 0}

@dataclass
class Packet:
    start: str
    end: str
    req_id: str
    color: tuple
    type: str # "req" or "resp"
    progress: float = 0.0
    trail: list = field(default_factory=list)
    alive: bool = True
    shatter: bool = False
    alpha: int = 255

@dataclass
class FrameState:
    node_status: dict
    active_module: dict
    active_req_id: dict
    emotion_counts: dict
    log_slice: list
    packet_snap: list
    ripples_snap: list
    popups_snap: list

def make_snapshot(log_scroll: int) -> FrameState:
    with lock:
        alive_packets = []
        for p in packets:
            if p.shatter:
                p.alpha -= 10
                if p.alpha <= 0: p.alive = False
            else:
                p.progress += 0.007
                sp = NODES[p.start]
                ep = NODES[p.end]
                
                # Shatter logic: if destination service is DOWN
                is_off = not svc_states.get(p.end, True)
                if is_off and p.progress > 0.4:
                    p.shatter = True
                    popups.append(Popup(ep[0], ep[1]-50, "DATA LOST", COLOR_NEON_RED))
                
                off = -15 if p.type == "req" else 15
                cx = int(sp[0] + (ep[0] - sp[0]) * p.progress)
                cy = int(sp[1] + off + (ep[1] - sp[1]) * p.progress)
                p.trail.append((cx, cy))
                if len(p.trail) > 15: p.trail.pop(0)
                
                if p.progress >= 1.0:
                    ripples.append(Ripple(ep[0], ep[1] + off, p.color))
                    p.alive = False
            
            if p.alive: alive_packets.append(p)
        
        packets[:] = alive_packets
        for r in ripples: r.update()
        ripples[:] = [r for r in ripples if r.alive]
        for p in popups: p.update()
        popups[:] = [p for p in popups if p.alive]

        return FrameState(
            node_status    = dict(node_status),
            active_module  = dict(active_module),
            active_req_id  = dict(active_req_id),
            emotion_counts = dict(emotion_counts),
            log_slice      = list(event_log[-(18 + log_scroll):][:18]),
            packet_snap    = [{"trail": list(pr.trail), "color": pr.color, "alpha": pr.alpha} for pr in packets],
            ripples_snap   = [{"x": r.x, "y": r.y, "radius": r.radius, "alpha": r.alpha, "color": r.color} for r in ripples],
            popups_snap    = [{"x": po.x, "y": po.y, "text": po.text, "color": po.color, "life": po.life} for po in popups]
        )

# ─────────────────────────────────────────────
#  UDP SERVER
# ─────────────────────────────────────────────
def _append_log(msg, color):
    ts = time.strftime("%H:%M:%S")
    event_log.append((ts, msg, color))
    if len(event_log) > 50: event_log.pop(0)

def process_event(ev):
    src, dst = ev.get("source"), ev.get("target")
    action, module = ev.get("action"), ev.get("module", "")
    req_id = ev.get("request_id", "UNK")
    
    color = COLOR_NEON_GREEN if "REQ" in action else COLOR_NEON_RED if "RESP" in action else COLOR_NEON_YELLOW
    _append_log(f"[{req_id[-4:]}] {src} -> {dst} ({action})", color)

    if action == "REQ_OUT" and src in NODES and dst in NODES:
        packets.append(Packet(src, dst, req_id, COLOR_NEON_GREEN, "req"))
        node_status[src] = "WAITING"
        active_module[src] = module
        active_req_id[src] = req_id
        ripples.append(Ripple(NODES[src][0], NODES[src][1]-15, COLOR_NEON_GREEN))

    elif action in ("REQ_IN", "PROCESSING"):
        if dst in NODES:
            node_status[dst] = "PROCESSING"
            active_module[dst] = module
            active_req_id[dst] = req_id

    elif action == "RESP_OUT" and src in NODES and dst in NODES:
        packets.append(Packet(src, dst, req_id, COLOR_NEON_RED, "resp"))
        active_module[src] = module

    elif action == "RESP_IN":
        if dst in NODES:
            node_status[dst] = "IDLE"
            active_module[dst] = ""

def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    try:
        sock.bind(("0.0.0.0", 9999))
    except Exception as e:
        _append_log(f"SOCKET ERROR: {e}", COLOR_NEON_RED)
        return
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            ev = json.loads(data.decode("utf-8"))
            with lock: process_event(ev)
        except: pass

threading.Thread(target=udp_server, daemon=True).start()

# ─────────────────────────────────────────────
#  DRAWING FUNCTIONS
# ─────────────────────────────────────────────
def draw_background():
    # Radial Gradient
    for r in range(0, 1000, 100):
        color = [max(0, c - r//10) for c in COLOR_BG_MID]
        pygame.draw.circle(screen, color, (CENTER_X := MAIN_W//2, CENTER_Y := NODE_AREA_H//2), 1200 - r)
    
    # Grid
    for x in range(0, MAIN_W, 60):
        pygame.draw.line(screen, (20, 25, 35), (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 60):
        pygame.draw.line(screen, (20, 25, 35), (0, y), (MAIN_W, y), 1)

def draw_glass_rect(surf, rect, color, border_color, glow=False, high_intensity=False):
    # Intensity multiplier for glow
    intensity = 3.0 if high_intensity else 1.0
    
    # Glow effect
    if glow:
        glow_layers = 15 if high_intensity else 8
        for i in range(1, glow_layers):
            alpha = int((120 if high_intensity else 100) / (i * (0.8 if high_intensity else 1.2)))
            if alpha <= 0: break
            pygame.draw.rect(surf, (*border_color, alpha), rect.inflate(i*2.2, i*2.2), border_radius=15)
    
    # Glint effect for high intensity
    final_color = color
    if high_intensity:
        glint = (math.sin(time.time() * 8) + 1) / 2
        # Blend a bit of the border color into the background
        final_color = (
            int(color[0] + (border_color[0] - color[0]) * 0.15 * glint),
            int(color[1] + (border_color[1] - color[1]) * 0.15 * glint),
            int(color[2] + (border_color[2] - color[2]) * 0.15 * glint),
            color[3]
        )

    # Base
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, final_color, (0, 0, *rect.size), border_radius=12)
    surf.blit(s, rect.topleft)
    
    # Border
    bw = 4 if high_intensity else 2
    pygame.draw.rect(surf, border_color, rect, width=bw, border_radius=12)

def draw_nodes_premium(fs: FrameState, mouse_pos):
    t = time.time()
    hover = None
    for name, (x, y) in NODES.items():
        rect = pygame.Rect(x - NW//2, y - NH//2, NW, NH)
        status = fs.node_status.get(name, "IDLE")
        
        if status == "PROCESSING":
            pulse = (math.sin(t * 8) + 1) / 2 # Faster pulse for processing
            b_color = [int(c1 + (c2-c1)*pulse) for c1, c2 in zip(COLOR_NEON_GREEN, (180, 255, 200))]
        elif status == "WAITING":
            pulse = (math.sin(t * 3) + 1) / 2
            # Cascading Failure effect: if next service is down, show blocking
            next_svc_map = {"USER": "Service_A", "Service_A": "Service_B", "Service_B": "Service_C"}
            nxt = next_svc_map.get(name)
            is_blocked = nxt and not svc_states.get(nxt, True)
            
            if is_blocked:
                b_color = COLOR_NEON_RED
                bt = F_SM.render("⚠️ BLOCKING", True, COLOR_NEON_RED)
                screen.blit(bt, (x - bt.get_width()//2, y + 45))
            else:
                b_color = [int(c1 + (c2-c1)*pulse) for c1, c2 in zip(COLOR_NEON_PURPLE, (220, 150, 255))]
        else:
            b_color = COLOR_GLASS_BDR

        is_high = (status == "PROCESSING")
        draw_glass_rect(screen, rect, COLOR_GLASS_BASE, b_color, glow=(status != "IDLE"), high_intensity=is_high)

        nt = F_NODE.render(name, True, WHITE)
        screen.blit(nt, (x - nt.get_width()//2, y - 35))
        st = F_SM.render(status, True, GRAY)
        screen.blit(st, (x - st.get_width()//2, y - 5))
        
        mod = fs.active_module.get(name)
        if mod and status != "IDLE":
            mt = F_TINY.render(mod, True, b_color)
            screen.blit(mt, (x - mt.get_width()//2, y + 20))

        if rect.collidepoint(mouse_pos): hover = name
    return hover

def draw_hud(fs: FrameState, input_box):
    px = MAIN_W
    pygame.draw.rect(screen, COLOR_BG_DEEP, (px, 0, LOG_W, HEIGHT))
    pygame.draw.line(screen, COLOR_GLASS_BDR, (px, 0), (px, HEIGHT), 2)
    
    lt = F_TITLE.render("SYSTEM EVENTS", True, COLOR_NEON_BLUE)
    screen.blit(lt, (px + 20, 20))
    
    y = 70
    for ts, msg, col in fs.log_slice:
        tst = F_TINY.render(ts, True, GRAY)
        screen.blit(tst, (px + 20, y))
        mt = F_TINY.render(msg[:35], True, col)
        screen.blit(mt, (px + 85, y))
        y += 22

    sy = NODE_AREA_H + CTRL_H
    pygame.draw.rect(screen, COLOR_BG_DEEP, (0, sy, MAIN_W, INPUT_H))
    
    sx = 40
    for emo, col in [("Happy", COLOR_NEON_GREEN), ("Sad", COLOR_NEON_BLUE), ("Angry", COLOR_NEON_RED)]:
        count = fs.emotion_counts.get(emo, 0)
        txt = F_BODY.render(f"{emo}: {count}", True, col)
        screen.blit(txt, (sx, sy + 60))
        sx += 180

# ─────────────────────────────────────────────
#  INPUT & LOGIC
# ─────────────────────────────────────────────
class TextInput:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.active = False

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN: self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN: return True
            else: self.text += event.unicode
        return False

    def draw(self, surf):
        color = COLOR_NEON_BLUE if self.active else COLOR_GLASS_BDR
        draw_glass_rect(surf, self.rect, (20, 20, 30), color)
        txt = self.text or "Enter sync message..."
        col = WHITE if self.text else GRAY
        ts = F_BODY.render(txt, True, col)
        surf.blit(ts, (self.rect.x + 15, self.rect.y + 10))

def send_req(text, emotion_counts):
    try:
        resp = requests.post("http://localhost:5000/api/post", 
                             json={"user": "student", "text": text},
                             headers={"Authorization": "Bearer super-secret-key"}, timeout=10)
        if resp.status_code == 200:
            emo = resp.json().get("emotion")
            if emo:
               with lock: emotion_counts[emo] += 1
    except: pass

PROJ_DIR = "/home/folium/Documents/Kafka/proj_without_kafka"
SVC_LIST = ["Service_A", "Service_B", "Service_C"]
# svc_states already initialized at top

SCENARIOS = {
    "RESET": {"Service_A": True, "Service_B": True, "Service_C": True},
    "S1: No A": {"Service_A": False, "Service_B": True, "Service_C": True},
    "S2: No B": {"Service_A": True, "Service_B": False, "Service_C": True},
    "S3: No C": {"Service_A": True, "Service_B": True, "Service_C": False},
    "S4: No A,B": {"Service_A": False, "Service_B": False, "Service_C": True},
    "S5: No A,C": {"Service_A": False, "Service_B": True, "Service_C": False},
    "S6: No B,C": {"Service_A": True, "Service_B": False, "Service_C": False},
    "S7: ALL OFF": {"Service_A": False, "Service_B": False, "Service_C": False},
}
SCENARIO_KEYS = list(SCENARIOS.keys())

def toggle_svc(svc):
    is_up = svc_states[svc]
    action = "stop" if is_up else "start"
    
    # Docker service names are lowercase in the yaml
    docker_svc = svc.lower()
    
    # Try docker-compose first, then docker compose
    cmds = [["docker-compose", action, docker_svc], ["docker", "compose", action, docker_svc]]
    success = False
    for cmd in cmds:
        try:
            subprocess.Popen(cmd, cwd=PROJ_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            success = True
            break
        except:
            continue
            
    if success:
        svc_states[svc] = not is_up
        with lock:
            _append_log(f"[CTRL] {svc} {'STOPPING' if is_up else 'STARTING'}...", COLOR_NEON_YELLOW)
    else:
        with lock:
            _append_log(f"[CTRL ERR] Could not run docker-compose", COLOR_NEON_RED)

def apply_scenario(scenario_name):
    targets = SCENARIOS.get(scenario_name)
    if not targets: return
    for svc, target_state in targets.items():
        if svc_states.get(svc, True) != target_state:
            threading.Thread(target=toggle_svc, args=(svc,), daemon=True).start()

input_box = TextInput(40, NODE_AREA_H + 90, 600, 45)
SEND_RECT = pygame.Rect(660, NODE_AREA_H + 90, 120, 45)

running = True
clock = pygame.time.Clock()
log_scroll = 0

try:
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False
            if input_box.handle(event):
                threading.Thread(target=send_req, args=(input_box.text, emotion_counts), daemon=True).start()
                input_box.text = ""
            if event.type == pygame.MOUSEBUTTONDOWN:
                if SEND_RECT.collidepoint(event.pos) and input_box.text:
                    threading.Thread(target=send_req, args=(input_box.text, emotion_counts), daemon=True).start()
                    input_box.text = ""
                for i, svc in enumerate(SVC_LIST):
                    btn_rect = pygame.Rect(40 + i*165, NODE_AREA_H + 20, 150, 40)
                    if btn_rect.collidepoint(event.pos):
                        threading.Thread(target=toggle_svc, args=(svc,), daemon=True).start()
                
                for i, s_key in enumerate(SCENARIO_KEYS):
                    btn_rect = pygame.Rect(40 + i*115, 800, 105, 40)
                    if btn_rect.collidepoint(event.pos):
                        apply_scenario(s_key)

        fs = make_snapshot(log_scroll)
        mouse_pos = pygame.mouse.get_pos()
        
        screen.fill(COLOR_BG_DEEP)
        draw_background()
        
        # Draw Connections
        pairs = [("USER", "Service_A"), ("Service_A", "Service_B"), ("Service_B", "Service_C")]
        for a, b in pairs:
            # Check if target is off
            target_off = not svc_states.get(b, True)
            l_col = COLOR_NEON_RED if target_off else (30, 40, 60)
            
            ay = NODES[a][1] - 15
            by = NODES[b][1] - 15
            
            if target_off:
                draw_dashed_line(screen, l_col, (NODES[a][0], ay), (NODES[b][0], by), 2)
                ot = F_TINY.render("OFFLINE", True, COLOR_NEON_RED)
                screen.blit(ot, ((NODES[a][0] + NODES[b][0])//2 - ot.get_width()//2, by - 25))
            else:
                pygame.draw.line(screen, l_col, (NODES[a][0], ay), (NODES[b][0], by), 1)
            
            # Return line
            pygame.draw.line(screen, (40, 30, 30), (NODES[b][0], NODES[b][1]+15), (NODES[a][0], NODES[a][1]+15), 1)

        for r in fs.ripples_snap:
            s = pygame.Surface((r["radius"]*2, r["radius"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*r["color"], r["alpha"]), (r["radius"], r["radius"]), r["radius"], 2)
            screen.blit(s, (r["x"] - r["radius"], r["y"] - r["radius"]))

        for p in fs.packet_snap:
            if len(p["trail"]) > 1:
                for i, pos in enumerate(p["trail"]):
                    alpha = int(p["alpha"] * (i / len(p["trail"])))
                    pygame.draw.circle(screen, (*p["color"], alpha), pos, 4)

        for p in fs.popups_snap:
            alpha = int(min(255, p["life"] * 255))
            st = F_SM.render(p["text"], True, (*p["color"], alpha))
            screen.blit(st, (p["x"] - st.get_width()//2, p["y"]))

        hover_node = draw_nodes_premium(fs, mouse_pos)
        draw_hud(fs, input_box)
        input_box.draw(screen)
        
        draw_glass_rect(screen, SEND_RECT, (40, 80, 50), COLOR_NEON_GREEN)
        st = F_BODY.render("SEND", True, WHITE)
        screen.blit(st, (SEND_RECT.centerx - st.get_width()//2, SEND_RECT.centery - st.get_height()//2))
        
        for i, svc in enumerate(SVC_LIST):
            rect = pygame.Rect(40 + i*165, NODE_AREA_H + 20, 150, 40)
            up = svc_states.get(svc, True)
            col = COLOR_NEON_GREEN if up else COLOR_NEON_RED
            draw_glass_rect(screen, rect, (20, 20, 30), col)
            lt = F_SM.render(svc.replace("_", " ").upper(), True, WHITE)
            screen.blit(lt, (rect.centerx - lt.get_width()//2, rect.centery - lt.get_height()//2))

        st = F_SM.render("SCENARIOS:", True, (130, 140, 160))
        screen.blit(st, (40, 775))
        for i, s_key in enumerate(SCENARIO_KEYS):
            rect = pygame.Rect(40 + i*115, 800, 105, 40)
            draw_glass_rect(screen, rect, (20, 20, 30), COLOR_NEON_YELLOW)
            lt = F_TINY.render(s_key, True, WHITE)
            screen.blit(lt, (rect.centerx - lt.get_width()//2, rect.centery - lt.get_height()//2))

        if hover_node:
            desc = NODE_DESC.get(hover_node, "").split("\n")
            tw = max(F_SM.size(l)[0] for l in desc) + 20
            th = len(desc) * 20 + 20
            tr = pygame.Rect(mouse_pos[0]+15, mouse_pos[1], tw, th)
            draw_glass_rect(screen, tr, (10, 10, 15, 230), COLOR_NEON_BLUE)
            for i, line in enumerate(desc):
                screen.blit(F_SM.render(line, True, WHITE), (tr.x+10, tr.y+10+i*20))

        pygame.display.flip()
        clock.tick(60)
except Exception as e: print(f"ERROR: {e}")
finally: pygame.quit()
