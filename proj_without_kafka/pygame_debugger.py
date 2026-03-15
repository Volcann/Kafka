import pygame
import socket
import json
import threading
import sys

pygame.init()

WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Microservices Real-Time Architecture Debugger")

# Define architecture nodes and positions
nodes = {
    "USER": (50, 300),
    "Service_A": (300, 300),
    "Service_B": (600, 300),
    "Service_C": (900, 300)
}

packets = [] 
node_status = {k: "IDLE" for k in nodes.keys()}
active_module = {k: "" for k in nodes.keys()}

lock = threading.Lock()

def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 9999))
    print("Debugger listening on UDP 9999...")
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            event = json.loads(data.decode('utf-8'))
            with lock:
                process_event(event)
        except Exception as e:
            print(f"Debugger error: {e}")

def process_event(event):
    src = event.get("source")
    dst = event.get("target")
    action = event.get("action")
    module = event.get("module", "")
    print(f"[EVENT] {src} -> {dst} : {action} [{module}]")
    
    if action == "REQ_OUT":
        if src in nodes and dst in nodes:
            packets.append({
                "start": src, "end": dst, "progress": 0.0, 
                "color": (50, 255, 50), "type": "req"  # Green for requests
            })
        if src in nodes:
            node_status[src] = "WAITING"
            active_module[src] = module
    elif action == "REQ_IN" or action == "PROCESSING":
        if dst in nodes:
            node_status[dst] = "PROCESSING"
            active_module[dst] = module
    elif action == "RESP_OUT":
        if src in nodes and dst in nodes:
            packets.append({
                "start": src, "end": dst, "progress": 0.0, 
                "color": (255, 50, 50), "type": "resp" # Red for responses
            })
        if src in nodes:
            active_module[src] = module
    elif action == "RESP_IN":
        if dst in nodes:
            node_status[dst] = "IDLE"
            active_module[dst] = ""

threading.Thread(target=udp_server, daemon=True).start()

font = pygame.font.SysFont("Segoe UI, Arial", 16, bold=True)
small_font = pygame.font.SysFont("Segoe UI, Arial", 12)

clock = pygame.time.Clock()
running = True

def draw_grid():
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, (30, 34, 40), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (30, 34, 40), (0, y), (WIDTH, y))

def draw_line(s, e):
    pygame.draw.line(screen, (100, 120, 150), nodes[s], nodes[e], 4)

while running:
    screen.fill((15, 18, 24))
    draw_grid()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    # Draw connections based on architecture
    draw_line("USER", "Service_A")
    draw_line("Service_A", "Service_B")
    draw_line("Service_B", "Service_C")
    
    # Draw nodes
    for name, pos in nodes.items():
        status = node_status.get(name, "IDLE")
        
        # Node color based on status
        if status == "PROCESSING":
            color = (255, 200, 0)
            glow_color = (255, 200, 0, 100)
        elif status == "WAITING":
            color = (150, 100, 150)
            glow_color = (150, 100, 150, 100)
        else:
            color = (50, 150, 220)
            glow_color = (50, 150, 220, 100)
            
        block_w, block_h = 120, 80
        rect = pygame.Rect(pos[0] - block_w//2, pos[1] - block_h//2, block_w, block_h)
        
        # Draw block body
        pygame.draw.rect(screen, (25, 30, 40), rect, border_radius=10)
        
        # Draw border
        pygame.draw.rect(screen, color, rect, width=3, border_radius=10)
        
        # Draw subtle header for node
        header_rect = pygame.Rect(pos[0] - block_w//2, pos[1] - block_h//2, block_w, 24)
        pygame.draw.rect(screen, color, header_rect, border_top_left_radius=10, border_top_right_radius=10)
        
        text = font.render(name, True, (255, 255, 255))
        screen.blit(text, (pos[0] - text.get_width()//2, pos[1] - block_h//2 + 2))
        
        # Subtext for status
        stext = small_font.render(status, True, (200, 220, 255) if status != "IDLE" else (100, 110, 120))
        screen.blit(stext, (pos[0] - stext.get_width()//2, pos[1] - 10))
            
        # Draw active module visualizer
        mod = active_module.get(name, "")
        if mod and status != "IDLE":
            mod_surface = small_font.render(mod, True, (20, 20, 20))
            box_rect = pygame.Rect(pos[0] - mod_surface.get_width()//2 - 6, pos[1] + 12, mod_surface.get_width() + 12, 20)
            pygame.draw.rect(screen, (120, 255, 120), box_rect, border_radius=4)
            screen.blit(mod_surface, (pos[0] - mod_surface.get_width()//2, pos[1] + 14))
        
    # Update and draw packets
    with lock:
        for p in packets:
            p["progress"] += 0.015  # Adjust speed here
            if p["progress"] > 1.0:
                p["progress"] = 1.0
            
            s = nodes.get(p["start"])
            e = nodes.get(p["end"])
            if s and e:
                x = s[0] + (e[0] - s[0]) * p["progress"]
                y = s[1] + (e[1] - s[1]) * p["progress"]
                
                # Draw blocky packet
                packet_rect = pygame.Rect(int(x) - 8, int(y) - 8, 16, 16)
                pygame.draw.rect(screen, p["color"], packet_rect, border_radius=3)
                pygame.draw.rect(screen, (255, 255, 255), packet_rect, width=1, border_radius=3)
                
        # Remove finished packets
        packets = [p for p in packets if p["progress"] < 1.0]

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
