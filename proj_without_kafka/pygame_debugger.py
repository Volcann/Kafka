import pygame
import socket
import json
import threading
import sys
import math
import requests
import time

pygame.init()

# 1. Increased Screen Size
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Microservices Real-Time Architecture Debugger")

# 2. Adjusted Node Positions for larger screen
nodes = {
    "USER": (100, 400),
    "Service_A": (400, 400),
    "Service_B": (750, 400),
    "Service_C": (1100, 400)
}

packets = [] 
node_status = {k: "IDLE" for k in nodes.keys()}
active_module = {k: "" for k in nodes.keys()}
active_req_id = {k: "" for k in nodes.keys()}
recent_logs = []
last_result = ""
last_result_color = (255, 255, 255)

lock = threading.Lock()

# 3. Interactive Input Handler
class TextInput:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = (40, 45, 55)
        self.text = "I love this project!"
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode

    def draw(self, screen):
        border_color = (100, 200, 255) if self.active else (60, 65, 75)
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)
        pygame.draw.rect(screen, border_color, self.rect, width=2, border_radius=5)
        txt = small_font.render(self.text, True, (255, 255, 255))
        screen.blit(txt, (self.rect.x + 10, self.rect.y + 10))

input_box = TextInput(400, 650, 400, 40)

def send_request(text_val):
    global last_result, last_result_color
    try:
        url = "http://localhost:5000/api/post"
        headers = {"Authorization": "Bearer super-secret-key"}
        payload = {"user": "pygame_user", "text": text_val}
        last_result = "Sending..."
        last_result_color = (200, 200, 200)
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            last_result = f"Success: {resp.json().get('emotion', 'Done')}"
            last_result_color = (100, 255, 100)
        else:
            last_result = f"Error: {resp.status_code}"
            last_result_color = (255, 100, 100)
    except Exception as e:
        last_result = f"Failed: {str(e)}"
        last_result_color = (255, 50, 50)

def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 9999))
    print("Debugger listening on UDP 9999...")
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            # Log raw data receipt for troubleshooting
            print(f"DEBUG: Received {len(data)} bytes from {addr}") 
            event = json.loads(data.decode('utf-8'))
            with lock:
                process_event(event)
        except Exception as e:
            print(f"Debugger error while receiving: {e}")

def process_event(event):
    src = event.get("source")
    dst = event.get("target")
    action = event.get("action")
    module = event.get("module", "")
    request_id = event.get("request_id", "UNKNOWN")
    
    # Restored Log Printing for Troubleshooting
    log_msg = f"[{request_id}] {src} -> {dst} : {action} [{module}]"
    print(f"EVENT: {log_msg}")
    
    if action == "REQ_OUT":
        if src in nodes and dst in nodes:
            packets.append({
                "start": src, "end": dst, "progress": 0.0, 
                "color": (50, 255, 50), "type": "req", "req_id": request_id, 
                "history": [] 
            })
        if src in nodes:
            node_status[src] = "WAITING"
            active_module[src] = module
            active_req_id[src] = request_id
    elif action == "REQ_IN" or action == "PROCESSING":
        if dst in nodes:
            node_status[dst] = "PROCESSING"
            active_module[dst] = module
            active_req_id[dst] = request_id
    elif action == "RESP_OUT":
        if src in nodes and dst in nodes:
            packets.append({
                "start": src, "end": dst, "progress": 0.0, 
                "color": (255, 50, 50), "type": "resp", "req_id": request_id,
                "history": [] 
            })
        if src in nodes:
            active_module[src] = module
            active_req_id[src] = request_id
    elif action == "RESP_IN":
        if dst in nodes:
            node_status[dst] = "IDLE"
            active_module[dst] = ""
            active_req_id[dst] = ""

threading.Thread(target=udp_server, daemon=True).start()

# Use generic fonts for better Docker compatibility
font = pygame.font.SysFont(None, 24, bold=True)
small_font = pygame.font.SysFont(None, 18)

clock = pygame.time.Clock()
running = True

def draw_grid():
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, (30, 34, 40), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (30, 34, 40), (0, y), (WIDTH, y))

# 4. Offset Drawing for Two-Way Visibility
def draw_line(s, e):
    s_pos = nodes[s]
    e_pos = nodes[e]
    # Draw two lines with slight offsets
    pygame.draw.line(screen, (40, 60, 80), (s_pos[0], s_pos[1]-10), (e_pos[0], e_pos[1]-10), 2) # REQ path
    pygame.draw.line(screen, (80, 40, 40), (s_pos[0], s_pos[1]+10), (e_pos[0], e_pos[1]+10), 2) # RESP path

while running:
    screen.fill((15, 18, 24))
    draw_grid()
    
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        input_box.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check Send Button
            send_btn = pygame.Rect(810, 650, 100, 40)
            if send_btn.collidepoint(event.pos):
                threading.Thread(target=send_request, args=(input_box.text,), daemon=True).start()
            
    # Draw connections
    draw_line("USER", "Service_A")
    draw_line("Service_A", "Service_B")
    draw_line("Service_B", "Service_C")
    
    # Draw nodes
    for name, pos in nodes.items():
        status = node_status.get(name, "IDLE")
        
        if status == "PROCESSING":
            pulse = (math.sin(time.time() * 1.5) + 1) / 2
            color = (int(200 + 55 * pulse), int(150 + 50 * pulse), 0)
        elif status == "WAITING":
            color = (150, 100, 255)
        else:
            color = (50, 150, 220)
            
        block_w, block_h = 150, 100
        rect = pygame.Rect(pos[0] - block_w//2, pos[1] - block_h//2, block_w, block_h)
        
        pygame.draw.rect(screen, (10, 12, 16), (rect.x+5, rect.y+5, block_w, block_h), border_radius=10)
        pygame.draw.rect(screen, (25, 30, 40), rect, border_radius=10)
        pygame.draw.rect(screen, color, rect, width=3, border_radius=10)
        
        header_rect = pygame.Rect(pos[0] - block_w//2, pos[1] - block_h//2, block_w, 28)
        pygame.draw.rect(screen, color, header_rect, border_top_left_radius=10, border_top_right_radius=10)
        
        text = font.render(name, True, (255, 255, 255))
        screen.blit(text, (pos[0] - text.get_width()//2, pos[1] - block_h//2 + 2))
        
        stext = small_font.render(status, True, (200, 220, 255) if status != "IDLE" else (100, 110, 120))
        screen.blit(stext, (pos[0] - stext.get_width()//2, pos[1] - 15))
            
        mod = active_module.get(name, "")
        if mod and status != "IDLE":
            mod_surface = small_font.render(mod, True, (20, 20, 20))
            box_rect = pygame.Rect(pos[0] - mod_surface.get_width()//2 - 6, pos[1] + 5, mod_surface.get_width() + 12, 22)
            pygame.draw.rect(screen, (120, 255, 120), box_rect, border_radius=4)
            screen.blit(mod_surface, (pos[0] - mod_surface.get_width()//2, pos[1] + 7))

        req_id = active_req_id.get(name, "")
        if req_id and status != "IDLE":
            req_text = small_font.render(req_id, True, (255, 200, 100))
            screen.blit(req_text, (pos[0] - req_text.get_width()//2, pos[1] + 32))
        
    # Update and draw packets
    with lock:
        for p in packets:
            s_pos = nodes.get(p["start"])
            e_pos = nodes.get(p["end"])
            if not s_pos or not e_pos:
                continue
                
            # Offset based on type
            offset = -10 if p["type"] == "req" else 10
            
            x = s_pos[0] + (e_pos[0] - s_pos[0]) * p["progress"]
            y = (s_pos[1] + offset) + (e_pos[1] - s_pos[1]) * p["progress"]
            
            p["history"].append((x, y))
            if len(p["history"]) > 30:
                p["history"].pop(0)
                
            if len(p["history"]) > 1:
                for i in range(len(p["history"]) - 1):
                    alpha = i / len(p["history"])
                    t_color = [int(c * alpha) for c in p["color"]]
                    pygame.draw.line(screen, t_color, p["history"][i], p["history"][i+1], max(1, int(4 * alpha)))

            p["progress"] += 0.005
            if p["progress"] >= 1.0:
                p["progress"] = 1.0
            
            packet_rect = pygame.Rect(int(x) - 8, int(y) - 8, 16, 16)
            pygame.draw.rect(screen, p["color"], packet_rect, border_radius=3)
            
            req_id = p.get("req_id", "")
            if req_id and req_id != "UNKNOWN":
                p_text = small_font.render(req_id, True, (255, 255, 255))
                screen.blit(p_text, (int(x) - p_text.get_width()//2, int(y) - 25))
                
        packets = [p for p in packets if p["progress"] < 1.0]

    # Draw Input Area
    pygame.draw.line(screen, (50, 55, 65), (0, 600), (WIDTH, 600), 2)
    label = font.render("Test Your Pipeline:", True, (255, 255, 255))
    screen.blit(label, (400, 615))
    
    input_box.draw(screen)
    
    # Send Button
    send_btn = pygame.Rect(810, 650, 100, 40)
    btn_color = (60, 180, 100) if send_btn.collidepoint(mouse_pos) else (40, 140, 80)
    pygame.draw.rect(screen, btn_color, send_btn, border_radius=5)
    btn_txt = small_font.render("SEND", True, (255, 255, 255))
    screen.blit(btn_txt, (send_btn.centerx - btn_txt.get_width()//2, send_btn.centery - btn_txt.get_height()//2))

    if last_result:
        res_txt = small_font.render(last_result, True, last_result_color)
        screen.blit(res_txt, (WIDTH//2 - res_txt.get_width()//2, 710))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
