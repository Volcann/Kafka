"""
Microservices Real-Time Request Debugger — PREMIUM KAFKA EDITION
=================================================================
A high-fidelity teaching tool visualizing asynchronous Kafka flows.

Features:
- Star Topology: Kafka Broker at the center.
- Deep Space Aesthetic: Radial gradients and particle effects.
- Glassmorphism: Frosted glass nodes with neon glows.
- Organic Animations: Breath-like pulsing and fluid message trails.
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
WIDTH, HEIGHT = 1400, 900
LOG_W         = 340
MAIN_W        = WIDTH - LOG_W
NODE_AREA_H   = 600
CTRL_H        = 80
INPUT_H       = HEIGHT - NODE_AREA_H - CTRL_H

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Kafka Debugger — Premium Edition")

# ─────────────────────────────────────────────
#  COLOUR PALETTE (Modern Dark)
# ─────────────────────────────────────────────
COLOR_BG_DEEP     = (8, 10, 15)
COLOR_BG_MID      = (15, 20, 30)
COLOR_GLASS_BASE  = (25, 30, 45, 160) # RGBA
COLOR_GLASS_BDR   = (70, 80, 110)
COLOR_NEON_BLUE   = (0, 180, 255)
COLOR_NEON_GREEN  = (50, 255, 130)
COLOR_NEON_ORANGE = (255, 140, 0)
COLOR_NEON_RED    = (255, 60, 80)
COLOR_NEON_PURPLE = (180, 100, 255)
COLOR_NEON_YELLOW = (255, 210, 60)
COLOR_KAFKA       = (255, 165, 0)

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
#  STAR TOPOLOGY LAYOUT
# ─────────────────────────────────────────────
CENTER_X = MAIN_W // 2
CENTER_Y = NODE_AREA_H // 2 + 40
RADIUS   = 220

# Broker is at the center
# Others are arranged in a circle
NODES = {
    "Broker":    (CENTER_X, CENTER_Y),
    "USER":      (CENTER_X + int(RADIUS * math.cos(math.radians(-160))), CENTER_Y + int(RADIUS * math.sin(math.radians(-160)))),
    "Service_A": (CENTER_X + int(RADIUS * math.cos(math.radians(-90))),  CENTER_Y + int(RADIUS * math.sin(math.radians(-90)))),
    "Service_B": (CENTER_X + int(RADIUS * math.cos(math.radians(20))),   CENTER_Y + int(RADIUS * math.sin(math.radians(20)))),
    "Service_C": (CENTER_X + int(RADIUS * math.cos(math.radians(110))),  CENTER_Y + int(RADIUS * math.sin(math.radians(110)))),
}

NW, NH = 160, 100

NODE_DESC = {
    "USER":      "Client Interface\nInitiates the HTTP request chain.",
    "Service_A": "Gateway Service\nProduces 'raw-messages' to Kafka.",
    "Broker":    "Kafka Cluster\nThe central nervous system of data.",
    "Service_B": "Analysis Engine\nConsumes raw, produces analyzed results.",
    "Service_C": "Live Dashboard\nConsumes results for real-time display.",
}

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

# ─────────────────────────────────────────────
#  SHARED STATE
# ─────────────────────────────────────────────
lock = threading.Lock()
node_status   = {k: "IDLE" for k in NODES}
active_module = {k: ""     for k in NODES}
active_req_id = {k: ""     for k in NODES}
packets: list = []
ripples: list = []
event_log: list = []
emotion_counts = {"Happy": 0, "Sad": 0, "Angry": 0}

@dataclass
class Packet:
    start: str
    end: str
    req_id: str
    color: tuple
    progress: float = 0.0
    trail: list = field(default_factory=list)
    
@dataclass
class FrameState:
    node_status: dict
    active_module: dict
    active_req_id: dict
    emotion_counts: dict
    log_slice: list
    packet_snap: list
    ripples_snap: list

def make_snapshot(log_scroll: int) -> FrameState:
    with lock:
        # Update Packets
        alive_packets = []
        for p in packets:
            p.progress += 0.008
            sp = NODES[p.start]
            ep = NODES[p.end]
            cx = int(sp[0] + (ep[0] - sp[0]) * p.progress)
            cy = int(sp[1] + (ep[1] - sp[1]) * p.progress)
            p.trail.append((cx, cy))
            if len(p.trail) > 15: p.trail.pop(0)
            if p.progress < 1.0:
                alive_packets.append(p)
            else:
                ripples.append(Ripple(ep[0], ep[1], p.color))
        
        packets[:] = alive_packets

        # Update Ripples
        for r in ripples: r.update()
        ripples[:] = [r for r in ripples if r.alive]

        return FrameState(
            node_status    = dict(node_status),
            active_module  = dict(active_module),
            active_req_id  = dict(active_req_id),
            emotion_counts = dict(emotion_counts),
            log_slice      = list(event_log[-(18 + log_scroll):][:18]),
            packet_snap    = [{"trail": list(p.trail), "color": p.color, "req_id": p.req_id} for p in packets],
            ripples_snap   = [{"x": r.x, "y": r.y, "radius": r.radius, "alpha": r.alpha, "color": r.color} for r in ripples]
        )

# ─────────────────────────────────────────────
#  UDP & LOG LOGIC
# ─────────────────────────────────────────────
def _append_log(msg, color):
    ts = time.strftime("%H:%M:%S")
    event_log.append((ts, msg, color))
    if len(event_log) > 50: event_log.pop(0)

def process_event(ev):
    src, dst = ev.get("source"), ev.get("target")
    action, module = ev.get("action"), ev.get("module", "")
    req_id = ev.get("request_id", "UNK")
    
    color = COLOR_NEON_GREEN if "REQ" in action else COLOR_NEON_RED
    _append_log(f"[{req_id[-4:]}] {src} -> {dst} ({action})", color)

    if action == "REQ_OUT" and src in NODES and dst in NODES:
        p_color = COLOR_KAFKA if "Broker" in (src, dst) else COLOR_NEON_GREEN
        packets.append(Packet(src, dst, req_id, p_color))
        node_status[src] = "WAITING" if src == "USER" else "PROCESSING"
        active_module[src] = module
        active_req_id[src] = req_id
        ripples.append(Ripple(NODES[src][0], NODES[src][1], p_color))

    elif action in ("REQ_IN", "PROCESSING"):
        if dst in NODES:
            node_status[dst] = "PROCESSING" if dst != "Broker" else "IDLE"
            active_module[dst] = module
            active_req_id[dst] = req_id

    elif action == "RESP_OUT" and src in NODES and dst in NODES:
        packets.append(Packet(src, dst, req_id, COLOR_NEON_RED))
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
#  DRAWING HELPERS (Premium Components)
# ─────────────────────────────────────────────
def draw_background():
    # Subtle Radial Gradient
    for r in range(0, 1000, 100):
        color = [max(0, c - r//10) for c in COLOR_BG_MID]
        pygame.draw.circle(screen, color, (CENTER_X, CENTER_Y), 1000 - r)
    
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
        
        # Determine Color Based on Status/Type
        if name == "Broker":
            b_color = COLOR_NEON_ORANGE
        elif status == "PROCESSING":
            pulse = (math.sin(t * 8) + 1) / 2 # Faster pulse for processing
            b_color = [int(c1 + (c2-c1)*pulse) for c1, c2 in zip(COLOR_NEON_GREEN, (180, 255, 200))]
        elif status == "WAITING":
            pulse = (math.sin(t * 3) + 1) / 2
            b_color = [int(c1 + (c2-c1)*pulse) for c1, c2 in zip(COLOR_NEON_PURPLE, (220, 150, 255))]
        else:
            b_color = COLOR_GLASS_BDR

        is_high = (status == "PROCESSING")
        draw_glass_rect(screen, rect, COLOR_GLASS_BASE, b_color, glow=(status != "IDLE" or name == "Broker"), high_intensity=is_high)

        # Text
        nt = F_NODE.render(name, True, WHITE)
        screen.blit(nt, (x - nt.get_width()//2, y - 35))
        
        st = F_SM.render(status if name != "Broker" else "KAFKA CLUSTER", True, GRAY)
        screen.blit(st, (x - st.get_width()//2, y - 5))
        
        mod = fs.active_module.get(name)
        if mod and status != "IDLE":
            mt = F_TINY.render(mod, True, b_color)
            screen.blit(mt, (x - mt.get_width()//2, y + 20))

        if rect.collidepoint(mouse_pos): hover = name
    return hover

def draw_hud(fs: FrameState, input_box):
    # Log Panel
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

    # Stats Strip
    sy = NODE_AREA_H + CTRL_H
    pygame.draw.rect(screen, COLOR_BG_DEEP, (0, sy, MAIN_W, INPUT_H))
    
    sx = 40
    for emo, col in [("Happy", COLOR_NEON_GREEN), ("Sad", COLOR_NEON_BLUE), ("Angry", COLOR_NEON_RED)]:
        count = fs.emotion_counts.get(emo, 0)
        txt = F_BODY.render(f"{emo}: {count}", True, col)
        screen.blit(txt, (sx, sy + 60))
        sx += 180

# ─────────────────────────────────────────────
#  MAIN LOOP & UI CLASSES
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
        txt = self.text or "Enter message..."
        col = WHITE if self.text else GRAY
        ts = F_BODY.render(txt, True, col)
        surf.blit(ts, (self.rect.x + 15, self.rect.y + 10))

def send_req(text):
    try:
        requests.post("http://localhost:5000/api/post", 
                      json={"user": "student", "text": text},
                      headers={"Authorization": "Bearer super-secret-key"}, timeout=5)
    except: pass

# Global Helpers for control buttons
PROJ_DIR = "/home/folium/Documents/Kafka/proj_with_kafka"
SVC_LIST = ["service_a", "service_b", "service_c", "kafka"]
svc_states = {s: True for s in SVC_LIST}

def toggle_svc(svc):
    is_up = svc_states[svc]
    action = "stop" if is_up else "start"
    
    # Try docker-compose first, then docker compose
    cmds = [["docker-compose", action, svc], ["docker", "compose", action, svc]]
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

# Init UI elements
input_box = TextInput(40, NODE_AREA_H + 90, 600, 45)
SEND_RECT = pygame.Rect(660, NODE_AREA_H + 90, 120, 45)

running = True
clock = pygame.time.Clock()
log_scroll = 0

try:
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if input_box.handle(event):
                threading.Thread(target=send_req, args=(input_box.text,), daemon=True).start()
                input_box.text = ""
            if event.type == pygame.MOUSEBUTTONDOWN:
                if SEND_RECT.collidepoint(event.pos) and input_box.text:
                    threading.Thread(target=send_req, args=(input_box.text,), daemon=True).start()
                    input_box.text = ""
                # Service Control Buttons (Simplistic for now)
                for i, svc in enumerate(SVC_LIST):
                    btn_rect = pygame.Rect(40 + i*160, NODE_AREA_H + 20, 140, 40)
                    if btn_rect.collidepoint(event.pos):
                        threading.Thread(target=toggle_svc, args=(svc,), daemon=True).start()

        # SNAPSHOT
        fs = make_snapshot(log_scroll)
        mouse_pos = pygame.mouse.get_pos()
        
        # RENDER
        screen.fill(COLOR_BG_DEEP)
        draw_background()
        
        # Connections (Faint Glow Lines)
        for name, pos in NODES.items():
            if name != "Broker":
                pygame.draw.line(screen, (30, 40, 60), NODES["Broker"], pos, 1)

        # Draw Ripples
        for r in fs.ripples_snap:
            s = pygame.Surface((r["radius"]*2, r["radius"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*r["color"], r["alpha"]), (r["radius"], r["radius"]), r["radius"], 2)
            screen.blit(s, (r["x"] - r["radius"], r["y"] - r["radius"]))

        # Draw Packets
        for p in fs.packet_snap:
            if len(p["trail"]) > 1:
                for i, pos in enumerate(p["trail"]):
                    alpha = int(255 * (i / len(p["trail"])))
                    pygame.draw.circle(screen, (*p["color"], alpha), pos, 4)

        hover_node = draw_nodes_premium(fs, mouse_pos)
        
        # HUD & INPUT
        draw_hud(fs, input_box)
        input_box.draw(screen)
        
        # Draw Buttons
        draw_glass_rect(screen, SEND_RECT, (40, 80, 50), COLOR_NEON_GREEN)
        st = F_BODY.render("SEND", True, WHITE)
        screen.blit(st, (SEND_RECT.centerx - st.get_width()//2, SEND_RECT.centery - st.get_height()//2))
        
        for i, svc in enumerate(SVC_LIST):
            rect = pygame.Rect(40 + i*160, NODE_AREA_H + 20, 140, 40)
            up = svc_states[svc]
            col = COLOR_NEON_GREEN if up else COLOR_NEON_RED
            draw_glass_rect(screen, rect, (20, 20, 30), col)
            lt = F_SM.render(svc.replace("_", " ").upper(), True, WHITE)
            screen.blit(lt, (rect.centerx - lt.get_width()//2, rect.centery - lt.get_height()//2))

        # Tooltip
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

except Exception as e:
    print(f"ERROR: {e}")
finally:
    pygame.quit()
