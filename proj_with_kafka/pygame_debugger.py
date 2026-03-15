"""
Microservices Real-Time Request Debugger (KAFKA VERSION)
=========================================================
Teaching tool — visualises Kafka message flow across microservices.

Flow:
1. USER -> Service_A (HTTP POST)
2. Service_A -> Broker (Kafka Produce: raw-messages)
3. Broker -> Service_B (Kafka Consume)
4. Service_B -> Broker (Kafka Produce: analyzed-messages)
5. Broker -> Service_C (Kafka Consume)
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
#  LAYOUT
# ─────────────────────────────────────────────
WIDTH, HEIGHT = 1400, 900
LOG_W         = 320
MAIN_W        = WIDTH - LOG_W
NODE_H        = 500
CTRL_H        = 70
INPUT_H       = HEIGHT - NODE_H - CTRL_H

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Microservices Request Debugger — Kafka Edition")

# ─────────────────────────────────────────────
#  COLOURS
# ─────────────────────────────────────────────
BG         = (13,  16,  22)
GRID_C     = (22,  26,  34)
PANEL_BG   = (18,  22,  30)
BORDER     = (40,  50,  65)
WHITE      = (255, 255, 255)
GRAY       = (140, 150, 165)
L_GRAY     = (200, 210, 225)
A_BLUE     = ( 60, 160, 255)
A_GRN      = ( 50, 230, 110)
A_RED      = (255,  80,  80)
A_YEL      = (255, 210,  60)
A_PUR      = (170, 100, 255)
IDLE_C     = ( 50, 130, 210)
HDR_DARK   = ( 10,  13,  18)
KAFKA_ORANGE = (255, 153, 51)

# ─────────────────────────────────────────────
#  FONTS
# ─────────────────────────────────────────────
F_TITLE = pygame.font.SysFont(None, 32, bold=True)
F_NODE  = pygame.font.SysFont(None, 26, bold=True)
F_BODY  = pygame.font.SysFont(None, 22)
F_SM    = pygame.font.SysFont(None, 18)
F_TINY  = pygame.font.SysFont(None, 15)

# ─────────────────────────────────────────────
#  NODE LAYOUT
# ─────────────────────────────────────────────
NY = NODE_H // 2

NODES = {
    "USER":      (int(MAIN_W * 0.08), NY),
    "Service_A": (int(MAIN_W * 0.28), NY),
    "Broker":    (int(MAIN_W * 0.50), NY),
    "Service_B": (int(MAIN_W * 0.72), NY),
    "Service_C": (int(MAIN_W * 0.92), NY),
}
NW, NH = 160, 110   # node box width/height

NODE_DESC = {
    "USER":      "Sends HTTP POST requests\nto the Gateway service.",
    "Service_A": "Gateway Service\nProduces messages to\nKafka 'raw-messages' topic.",
    "Broker":    "Apache Kafka Broker\nDecouples services via\ntopics and partitions.",
    "Service_B": "Sentiment Analyser\nConsumes raw, processes,\nand produces analyzed data.",
    "Service_C": "Dashboard Counter\nConsumes analyzed data\nand updates Web UI.",
}
NODE_PORTS = {"Service_A": "5000", "Broker": "9092", "Service_B": ":-", "Service_C": "5003"}

# ─────────────────────────────────────────────
#  SHARED STATE  (written by UDP thread)
# ─────────────────────────────────────────────
lock = threading.Lock()

# Node state (protected by lock)
node_status   = {k: "IDLE" for k in NODES}
active_module = {k: ""     for k in NODES}
active_req_id = {k: ""     for k in NODES}

# Packets: each dict has {start, end, progress, color, type, req_id, trail, cx, cy}
packets: list = []
MAX_PACKETS = 30

# Event log: list of (time_str, msg, color)
event_log: list = []
MAX_LOG = 50

# Emotion counters
emotion_counts = {"Happy": 0, "Sad": 0, "Angry": 0}

# ─────────────────────────────────────────────
#  PER-FRAME SNAPSHOT  (read by render thread)
# ─────────────────────────────────────────────
@dataclass
class FrameState:
    node_status:   dict  = field(default_factory=dict)
    active_module: dict  = field(default_factory=dict)
    active_req_id: dict  = field(default_factory=dict)
    emotion_counts: dict = field(default_factory=dict)
    log_slice:     list  = field(default_factory=list)
    packet_snap:   list  = field(default_factory=list)


def make_snapshot(log_scroll: int) -> FrameState:
    """Grab lock ONCE, copy everything needed for one frame."""
    with lock:
        # Advance packets & build trail
        alive = []
        for p in packets:
            sp = NODES.get(p["start"])
            ep = NODES.get(p["end"])
            if sp and ep:
                off = -14 if p["type"] == "req" else 14
                x = int(sp[0] + (ep[0] - sp[0]) * p["progress"])
                y = int((sp[1] + off) + (ep[1] - sp[1]) * p["progress"])
                p["trail"].append((x, y))
                if len(p["trail"]) > 20:
                    p["trail"].pop(0)
                p["cx"] = x
                p["cy"] = y
                p["progress"] += 0.006 # Speed up a bit
            if p["progress"] < 1.0:
                alive.append(p)
        packets.clear()
        packets.extend(alive)

        fs = FrameState(
            node_status    = dict(node_status),
            active_module  = dict(active_module),
            active_req_id  = dict(active_req_id),
            emotion_counts = dict(emotion_counts),
            log_slice      = list(event_log[-(LOG_VISIBLE + log_scroll):][:LOG_VISIBLE]),
            packet_snap    = [
                {
                    "color":  p["color"],
                    "trail":  list(p["trail"]),
                    "cx":     p["cx"],
                    "cy":     p["cy"],
                    "req_id": p["req_id"],
                }
                for p in packets
            ],
        )
    return fs


LOG_VISIBLE = 18

# ─────────────────────────────────────────────
#  UDP EVENT RECEIVER
# ─────────────────────────────────────────────
ACTION_COLORS = {
    "REQ_OUT":    A_GRN,
    "REQ_IN":     (100, 230, 130),
    "RESP_OUT":   A_YEL,
    "RESP_IN":    (255, 230, 100),
    "PROCESSING": A_PUR,
}


def _append_log(msg: str, color: tuple):
    ts = time.strftime("%H:%M:%S")
    event_log.append((ts, msg, color))
    if len(event_log) > MAX_LOG:
        event_log.pop(0)


def process_event(ev: dict):
    src    = ev.get("source", "?")
    dst    = ev.get("target", "?")
    action = ev.get("action", "?")
    module = ev.get("module", "")
    req_id = ev.get("request_id", "UNKNOWN")

    color = ACTION_COLORS.get(action, L_GRAY)
    _append_log(f"[{req_id[-6:]}] {src}→{dst}  {action}", color)
    if module:
        _append_log(f"   module: {module}", GRAY)

    if action == "REQ_OUT":
        if src in NODES and dst in NODES and len(packets) < MAX_PACKETS:
            # Color it orange if it's Kafka
            p_color = KAFKA_ORANGE if dst == "Broker" or src == "Broker" else A_GRN
            packets.append({
                "start": src, "end": dst, "progress": 0.0,
                "color": p_color, "type": "req", "req_id": req_id,
                "trail": [], "cx": 0, "cy": 0,
            })
        if src in NODES:
            # If src is USER or Service_A producing, mark as WAITING if not Broker
            if src != "Broker":
               node_status[src]   = "WAITING" if src == "USER" else "PROCESSING"
               active_module[src] = module
               active_req_id[src] = req_id

    elif action in ("REQ_IN", "PROCESSING"):
        if dst in NODES:
            node_status[dst]   = "PROCESSING"
            active_module[dst] = module
            active_req_id[dst] = req_id
        if action == "REQ_IN" and dst == "Broker":
            # Just bounce off Broker
            node_status[dst] = "IDLE"

    elif action == "RESP_OUT":
        if src in NODES and dst in NODES and len(packets) < MAX_PACKETS:
            p_color = KAFKA_ORANGE if dst == "Broker" or src == "Broker" else A_RED
            packets.append({
                "start": src, "end": dst, "progress": 0.0,
                "color": p_color, "type": "resp", "req_id": req_id,
                "trail": [], "cx": 0, "cy": 0,
            })
        if src in NODES:
            active_module[src] = module
            active_req_id[src] = req_id

    elif action == "RESP_IN":
        if dst in NODES:
            node_status[dst]   = "IDLE"
            active_module[dst] = ""
            active_req_id[dst] = ""


def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 9999))
    sock.settimeout(1.0)
    print("Debugger listening on UDP port 9999…")
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            ev = json.loads(data.decode("utf-8"))
            with lock:
                process_event(ev)
        except socket.timeout:
            pass
        except Exception as exc:
            print(f"UDP error: {exc}")


threading.Thread(target=udp_server, daemon=True).start()

# ─────────────────────────────────────────────
#  HTTP SEND (runs in thread)
# ─────────────────────────────────────────────
last_result       = ""
last_result_color = WHITE


def send_request(text: str):
    global last_result, last_result_color
    try:
        last_result       = "Sending HTTP..."
        last_result_color = GRAY
        resp = requests.post(
            "http://localhost:5000/api/post",
            json    = {"user": "student", "text": text},
            headers = {"Authorization": "Bearer super-secret-key"},
            timeout = 10,
        )
        if resp.status_code == 202:
            last_result       = "Service A: Accepted (Kafka Flow Started)"
            last_result_color = A_GRN
        else:
            last_result       = f"HTTP {resp.status_code}"
            last_result_color = A_RED
    except Exception as exc:
        last_result       = f"Error: {str(exc)[:55]}"
        last_result_color = A_RED

# ─────────────────────────────────────────────
#  SERVICE CONTROL
# ─────────────────────────────────────────────
PROJ_DIR = "/home/folium/Documents/Kafka/proj_with_kafka"
SVC_LIST  = ["service_a", "service_b", "service_c", "kafka"]
SVC_LABEL = ["Service A", "Service B", "Service C", "Kafka Broker"]
svc_states = {s: True for s in SVC_LIST}


def toggle_service(svc: str):
    is_up = svc_states.get(svc, True)
    action = "stop" if is_up else "start"
    try:
        subprocess.Popen(["docker-compose", action, svc], cwd=PROJ_DIR,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        svc_states[svc] = not is_up
        with lock:
            _append_log(f"[CTRL] {svc} {'STOPPED' if is_up else 'STARTED'}", A_YEL)
    except Exception as exc:
        with lock:
            _append_log(f"[CTRL ERR] {exc}", A_RED)

# ─────────────────────────────────────────────
#  TEXT INPUT
# ─────────────────────────────────────────────
class TextInput:
    def __init__(self, x, y, w, h):
        self.rect   = pygame.Rect(x, y, w, h)
        self.text   = ""
        self.active = False
        self._tick  = 0
        self._cvis  = True

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key not in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.text += event.unicode

    def draw(self, surf):
        self._tick += 1
        if self._tick > 30:
            self._cvis = not self._cvis
            self._tick = 0

        bc = A_BLUE if self.active else BORDER
        pygame.draw.rect(surf, (20, 25, 35), self.rect, border_radius=8)
        pygame.draw.rect(surf, bc, self.rect, width=2, border_radius=8)

        txt  = self.text or "Type message for Kafka flow..."
        col  = WHITE if self.text else GRAY
        surf_t = F_BODY.render(txt, True, col)
        surf.blit(surf_t, (self.rect.x + 12,
                            self.rect.centery - surf_t.get_height() // 2))

        if self.active and self._cvis and self.text:
            cx = self.rect.x + 12 + surf_t.get_width() + 2
            cy = self.rect.centery - 10
            pygame.draw.line(surf, WHITE, (cx, cy), (cx, cy + 20), 2)

# ─────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────
def draw_grid():
    for x in range(0, MAIN_W, 40):
        pygame.draw.line(screen, GRID_C, (x, 0), (x, NODE_H + CTRL_H))
    for y in range(0, NODE_H + CTRL_H, 40):
        pygame.draw.line(screen, GRID_C, (0, y), (MAIN_W, y))


def draw_arrow(color, start, end, width=2, sz=9):
    pygame.draw.line(screen, color, start, end, width)
    dx, dy = end[0] - start[0], end[1] - start[1]
    dist   = math.hypot(dx, dy)
    if dist == 0:
        return
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux
    b1 = (end[0] - ux*sz + px*sz*0.5, end[1] - uy*sz + py*sz*0.5)
    b2 = (end[0] - ux*sz - px*sz*0.5, end[1] - uy*sz - py*sz*0.5)
    pygame.draw.polygon(screen, color, [end, b1, b2])


def draw_connections():
    # USER -> Service_A (HTTP)
    draw_arrow(A_GRN, (NODES["USER"][0] + NW//2, NY - 14), (NODES["Service_A"][0] - NW//2, NY - 14))
    
    # Service_A -> Broker (Kafka Produce)
    draw_arrow(KAFKA_ORANGE, (NODES["Service_A"][0] + NW//2, NY - 20), (NODES["Broker"][0] - NW//2, NY - 20))
    
    # Broker -> Service_B (Kafka Consume)
    draw_arrow(KAFKA_ORANGE, (NODES["Broker"][0] + NW//2, NY - 20), (NODES["Service_B"][0] - NW//2, NY - 20))
    
    # Service_B -> Broker (Kafka Produce Result)
    draw_arrow(KAFKA_ORANGE, (NODES["Service_B"][0] - NW//2, NY + 20), (NODES["Broker"][0] + NW//2, NY + 20))
    
    # Broker -> Service_C (Kafka Consume Result)
    draw_arrow(KAFKA_ORANGE, (NODES["Broker"][0] + NW//2, NY + 20), (NODES["Service_C"][0] - NW//2, NY + 20))

    # Labels
    mx1 = (NODES["USER"][0] + NODES["Service_A"][0]) // 2
    screen.blit(F_TINY.render("HTTP POST", True, A_GRN), (mx1 - 30, NY - 32))
    
    mx2 = (NODES["Service_A"][0] + NODES["Broker"][0]) // 2
    screen.blit(F_TINY.render("PRODUCE", True, KAFKA_ORANGE), (mx2 - 30, NY - 38))

    mx3 = (NODES["Broker"][0] + NODES["Service_B"][0]) // 2
    screen.blit(F_TINY.render("CONSUME", True, KAFKA_ORANGE), (mx3 - 30, NY - 38))
    
    mx4 = (NODES["Service_B"][0] + NODES["Broker"][0]) // 2
    screen.blit(F_TINY.render("PRODUCE RES", True, KAFKA_ORANGE), (mx4 - 40, NY + 28))
    
    mx5 = (NODES["Broker"][0] + NODES["Service_C"][0]) // 2
    screen.blit(F_TINY.render("CONSUME RES", True, KAFKA_ORANGE), (mx5 - 40, NY + 28))


def draw_nodes(fs: FrameState, mouse_pos):
    hover = None
    t = time.time()
    for name, pos in NODES.items():
        status = fs.node_status.get(name, "IDLE")
        rect   = pygame.Rect(pos[0]-NW//2, pos[1]-NH//2, NW, NH)

        if name == "Broker":
            bdr = KAFKA_ORANGE
        elif status == "PROCESSING":
            pulse  = (math.sin(t * 2.5) + 1) / 2
            bdr    = (int(220 + 35*pulse), int(160 + 50*pulse), 0)
        elif status == "WAITING":
            pulse  = (math.sin(t * 3.0) + 1) / 2
            bdr    = (int(130 + 40*pulse), int(70 + 30*pulse), 255)
        else:
            bdr    = IDLE_C

        # Shadow
        pygame.draw.rect(screen, (6,8,12),
                         (rect.x+5, rect.y+5, NW, NH), border_radius=12)
        pygame.draw.rect(screen, (22,28,40), rect, border_radius=12)
        pygame.draw.rect(screen, bdr, rect, width=3, border_radius=12)

        # Header
        hdr = pygame.Rect(rect.x, rect.y, NW, 32)
        pygame.draw.rect(screen, bdr, hdr,
                         border_top_left_radius=12, border_top_right_radius=12)

        ns = F_NODE.render(name, True, WHITE)
        screen.blit(ns, (rect.centerx - ns.get_width()//2, rect.y + 6))

        sc = A_YEL if status == "PROCESSING" else A_PUR if status == "WAITING" else GRAY
        ss = F_SM.render(status if name != "Broker" else "ACTIVE", True, sc)
        screen.blit(ss, (rect.centerx - ss.get_width()//2, rect.y + 36))

        mod = fs.active_module.get(name, "")
        if mod and status != "IDLE":
            ms   = F_SM.render(mod, True, (10,20,10))
            pill = pygame.Rect(rect.centerx - ms.get_width()//2 - 6,
                               rect.y + 55, ms.get_width()+12, 20)
            pygame.draw.rect(screen, A_GRN if "HTTP" in mod else KAFKA_ORANGE, pill, border_radius=5)
            screen.blit(ms, (rect.centerx - ms.get_width()//2, rect.y + 57))

        rid = fs.active_req_id.get(name, "")
        if rid and status != "IDLE":
            rs = F_TINY.render(rid[-10:], True, A_YEL)
            screen.blit(rs, (rect.centerx - rs.get_width()//2, rect.y + 80))

        port = NODE_PORTS.get(name, "")
        if port:
            ps = F_TINY.render(f":{port}", True, GRAY)
            screen.blit(ps, (rect.centerx - ps.get_width()//2, rect.bottom + 5))

        if rect.collidepoint(mouse_pos):
            hover = name

    return hover


def draw_tooltip(hover_name, mouse_pos):
    if not hover_name:
        return
    desc    = NODE_DESC.get(hover_name, "")
    lines   = desc.split("\n")
    pad, lh = 10, 20
    tw      = max(F_SM.size(ln)[0] for ln in lines) + pad*2
    th      = len(lines) * lh + pad*2
    tx      = min(mouse_pos[0] + 14, MAIN_W - tw - 4)
    ty      = max(4, min(mouse_pos[1] - th//2, HEIGHT - th - 4))

    pygame.draw.rect(screen, BORDER,    (tx-2, ty-2, tw+4, th+4), border_radius=6)
    pygame.draw.rect(screen, (28,34,46),(tx,   ty,   tw,   th),   border_radius=6)
    for i, ln in enumerate(lines):
        ls = F_SM.render(ln, True, L_GRAY)
        screen.blit(ls, (tx + pad, ty + pad + i*lh))


def draw_packets_snap(snap: list):
    for p in snap:
        trail = p["trail"]
        if len(trail) > 1:
            for i in range(len(trail) - 1):
                alpha   = i / len(trail)
                tc      = tuple(int(c * alpha) for c in p["color"])
                pygame.draw.line(screen, tc, trail[i], trail[i+1],
                                 max(1, int(3 * alpha)))
        cx, cy = p["cx"], p["cy"]
        if cx == 0 and cy == 0:
            continue
        pygame.draw.circle(screen, p["color"], (cx, cy), 9)
        pygame.draw.circle(screen, WHITE,      (cx, cy), 9, 1)


def draw_log_panel(log_slice: list):
    px = MAIN_W
    pygame.draw.rect(screen, PANEL_BG, (px, 0, LOG_W, HEIGHT))
    pygame.draw.line(screen, BORDER, (px, 0), (px, HEIGHT), 2)

    pygame.draw.rect(screen, (20,26,36), (px, 0, LOG_W, 40))
    ts = F_BODY.render("Kafka Event Log", True, KAFKA_ORANGE)
    screen.blit(ts, (px + LOG_W//2 - ts.get_width()//2, 10))

    y = 48
    for ts_str, msg, color in log_slice:
        tss = F_TINY.render(ts_str, True, (80,90,110))
        screen.blit(tss, (px + 6, y))
        ms  = F_TINY.render(msg[:42], True, color)
        screen.blit(ms, (px + 60, y))
        y += 18
        if y > HEIGHT - 180:
            break


def draw_ctrl_strip(mouse_pos):
    cy = NODE_H
    pygame.draw.rect(screen, (16,20,28), (0, cy, MAIN_W, CTRL_H))
    pygame.draw.line(screen, BORDER, (0, cy), (MAIN_W, cy), 1)
    screen.blit(F_SM.render("Service Controls:", True, GRAY), (14, cy + 26))

    bw, bh = 180, 38
    gap    = 15
    block  = len(SVC_LIST)*bw + (len(SVC_LIST)-1)*gap
    sx     = (MAIN_W - block) // 2
    rects  = {}
    for i, svc in enumerate(SVC_LIST):
        rx = sx + i*(bw+gap)
        ry = cy + (CTRL_H - bh)//2
        r  = pygame.Rect(rx, ry, bw, bh)
        rects[svc] = r
        up   = svc_states.get(svc, True)
        hov  = r.collidepoint(mouse_pos)
        bgc  = (30,100,55) if up else (80,30,30)
        if hov:
            bgc = (40,140,75) if up else (110,40,40)
        brc  = A_GRN if up else A_RED
        lbl  = f"{'■' if up else '▶'} {SVC_LABEL[i]}"
        pygame.draw.rect(screen, bgc, r, border_radius=7)
        pygame.draw.rect(screen, brc, r, width=2, border_radius=7)
        ls = F_SM.render(lbl, True, WHITE)
        screen.blit(ls, (r.centerx - ls.get_width()//2, r.centery - ls.get_height()//2))
    return rects


def draw_input_area(mouse_pos, input_box, send_rect, clear_rect, fs: FrameState):
    ay = NODE_H + CTRL_H
    pygame.draw.rect(screen, (14,18,26), (0, ay, MAIN_W, INPUT_H))
    pygame.draw.line(screen, BORDER, (0, ay), (MAIN_W, ay), 1)

    screen.blit(F_BODY.render("Trigger Kafka Pipeline:", True, L_GRAY), (int(MAIN_W*0.10), ay+6))
    input_box.draw(screen)

    sc = (50,180,100) if send_rect.collidepoint(mouse_pos) else (35,140,75)
    pygame.draw.rect(screen, sc, send_rect, border_radius=8)
    pygame.draw.rect(screen, A_GRN, send_rect, width=2, border_radius=8)
    ss = F_BODY.render("SEND", True, WHITE)
    screen.blit(ss, (send_rect.centerx - ss.get_width()//2,
                     send_rect.centery - ss.get_height()//2))

    cc = (70,30,30) if clear_rect.collidepoint(mouse_pos) else (50,22,22)
    pygame.draw.rect(screen, cc, clear_rect, border_radius=8)
    pygame.draw.rect(screen, A_RED, clear_rect, width=2, border_radius=8)
    cs = F_BODY.render("CLEAR", True, WHITE)
    screen.blit(cs, (clear_rect.centerx - cs.get_width()//2,
                     clear_rect.centery - cs.get_height()//2))

    if last_result:
        rs = F_BODY.render(last_result, True, last_result_color)
        screen.blit(rs, (int(MAIN_W*0.10), ay + 80))

    # Emotion stats
    sx = int(MAIN_W * 0.48)
    emo_row = [("Happy", A_GRN), ("Sad", A_BLUE), ("Angry", A_RED)]
    for emo, col in emo_row:
        label = f"{emo}: {fs.emotion_counts.get(emo, 0)}"
        es    = F_BODY.render(label, True, col)
        screen.blit(es, (sx, ay + 80))
        sx += es.get_width() + 30


def draw_title_bar():
    pygame.draw.rect(screen, HDR_DARK, (0, 0, MAIN_W, 36))
    pygame.draw.line(screen, BORDER, (0, 36), (MAIN_W, 36), 1)
    title = F_TITLE.render("Microservices Request Debugger — KAFKA MODE", True, KAFKA_ORANGE)
    screen.blit(title, (MAIN_W//2 - title.get_width()//2, 7))
    ct = F_SM.render(time.strftime("%H:%M:%S"), True, GRAY)
    screen.blit(ct, (MAIN_W - ct.get_width() - 12, 11))


_ib_y   = NODE_H + CTRL_H + 28
input_box  = TextInput(int(MAIN_W*0.10), _ib_y, int(MAIN_W*0.52), 40)
SEND_RECT  = pygame.Rect(int(MAIN_W*0.64), _ib_y, 110, 40)
CLEAR_RECT = pygame.Rect(int(MAIN_W*0.64) + 120, _ib_y, 90, 40)

running = True
def _quit(sig, frame):
    global running
    running = False
signal.signal(signal.SIGINT,  _quit)
signal.signal(signal.SIGTERM, _quit)

clock      = pygame.time.Clock()
log_scroll = 0
ctrl_rects: dict = {}
hover_node = None

try:
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if input_box.active and input_box.text.strip():
                        threading.Thread(target=send_request, args=(input_box.text,), daemon=True).start()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if SEND_RECT.collidepoint(event.pos) and input_box.text.strip():
                    threading.Thread(target=send_request, args=(input_box.text,), daemon=True).start()
                if CLEAR_RECT.collidepoint(event.pos):
                    input_box.text = ""
                    last_result    = ""
                for svc, r in ctrl_rects.items():
                    if r.collidepoint(event.pos):
                        threading.Thread(target=toggle_service, args=(svc,), daemon=True).start()
            elif event.type == pygame.MOUSEWHEEL:
                if pygame.mouse.get_pos()[0] > MAIN_W:
                    log_scroll = max(0, min(log_scroll - event.y, max(0, len(event_log) - LOG_VISIBLE)))
            input_box.handle(event)

        fs = make_snapshot(log_scroll)
        mouse_pos = pygame.mouse.get_pos()

        screen.fill(BG)
        draw_grid()
        draw_title_bar()
        draw_connections()
        hover_node = draw_nodes(fs, mouse_pos)
        draw_packets_snap(fs.packet_snap)
        ctrl_rects = draw_ctrl_strip(mouse_pos)
        draw_input_area(mouse_pos, input_box, SEND_RECT, CLEAR_RECT, fs)
        draw_log_panel(fs.log_slice)
        draw_tooltip(hover_node, mouse_pos)

        pygame.display.flip()
        clock.tick(30)

except Exception as exc:
    print(f"[DEBUGGER] Fatal error: {exc}")
    import traceback
    traceback.print_exc()
finally:
    pygame.quit()
    sys.exit()
