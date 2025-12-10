import socket
import threading
import json
import pygame
import sys

from protocol import serialize_message

# -------------------- CONFIGURAÇÃO DO SERVIDOR ----------------------
SERVER_HOST = "127.0.0.1"  # IP do servidor
SERVER_PORT = 65432        # Porta do servidor

# -------------------- INICIALIZAÇÃO DO PYGAME ----------------------
pygame.init()
W, H = 520, 720            # Largura e altura da janela
BOARD_H = 500               # Altura do painel do tabuleiro
CELL = BOARD_H // 3         # Tamanho de cada célula do tabuleiro

# Cores usadas na interface
BG_TOP = (235, 220, 255) 
BG_BOTTOM = (210, 185, 255)
COR_X = (255, 0, 144)
COR_O = (85, 107, 47)
WHITE = (245, 245, 245)
BLACK = (0, 0, 0)
LINE = (245, 245, 245)

# Configura janela e título
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Jogo da Velha (TCP)")

# Fontes para textos em diferentes tamanhos
font_big = pygame.font.SysFont("arial", 120, bold=True)
font_mid = pygame.font.SysFont("arial", 54, bold=True)
font_status = pygame.font.SysFont("arial", 32, bold=True)
font_small = pygame.font.SysFont("arial", 26)

# Carrega a imagem de flor
try:
    img = pygame.image.load("flor.png").convert_alpha()
    img = pygame.transform.scale(img, (100, 100))
    use_img = True
except Exception:
    img = None
    use_img = False

# -------------------- ESTADO INTERNO DO CLIENTE ----------------------
sock = None               # Socket TCP do cliente
role = "S"                # Papel do cliente: X / O / S (espectador)
board = [[" "]*3 for _ in range(3)]  # Tabuleiro local
current = "X"             # Quem joga agora
game_over = False         # Flag de fim de jogo
winner = None             # Vencedor
players = 0               # Número de jogadores conectados

ui_mode = "MENU"          # Estado da interface: MENU / GAME
status_text = "Conectando ao servidor..."  # Linha de status
lock = threading.Lock()   # Lock para proteger variáveis compartilhadas

# -------------------- FUNÇÕES DE DESENHO ----------------------

def paint_gradient():
    """
    Preenche a tela com gradiente vertical de cores.
    """
    for y in range(H):
        t = y / (H - 1)
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        screen.fill((r, g, b), rect=pygame.Rect(0, 0, W, H))

def draw_board():
    """
    Desenha o painel do tabuleiro, linhas e X/O.
    """
    # Painel do tabuleiro com cantos arredondados
    pygame.draw.rect(screen, (250, 170, 180), (10, 10, W - 20, BOARD_H), border_radius=14)

    board_left = 10
    board_top = 10
    board_right = board_left + BOARD_H
    board_bottom = board_top + BOARD_H

    # Linhas da grade
    for i in range(1, 3):
        # linhas verticais
        x = board_left + i * CELL
        pygame.draw.line(screen, LINE, (x, board_top), (x, board_bottom), 5)

        # linhas horizontais
        y = board_top + i * CELL
        pygame.draw.line(screen, LINE, (board_left, y), (board_right, y), 5)

    # Desenha X ou O nas células
    for r in range(3):
        for c in range(3):
            sym = board[r][c]
            if sym.strip():
                color = COR_X if sym == "X" else COR_O
                txt = font_big.render(sym, True, color)
                cx = 10 + c * CELL + CELL // 2
                cy = 10 + r * CELL + CELL // 2
                rect = txt.get_rect(center=(cx, cy))
                screen.blit(txt, rect)

def button(label, y, active=True):
    """
    Desenha um botão com rótulo na posição vertical `y`.
    Retorna o rect para detectar clique.
    """
    w, h = 200, 46
    x = (W - w) // 2
    rect = pygame.Rect(x, y, w, h)

    bg = (255, 200, 220) if active else (235, 180, 200)
    border = (255, 240, 250) if active else (220, 180, 200)

    pygame.draw.rect(screen, bg, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, 2, border_radius=10)

    txt = font_small.render(label, True, BLACK)
    screen.blit(txt, (x + (w - txt.get_width()) // 2,
                      y + (h - txt.get_height()) // 2))
    return rect

def status_line():
    """
    Desenha a linha de status com mensagem atual.
    """
    pygame.draw.rect(screen, BG_BOTTOM, (10, BOARD_H + 20, W - 20, 70), border_radius=12)
    text = font_status.render(status_text, True, BLACK)
    text_rect = text.get_rect(center=(W // 2, BOARD_H + 55))
    screen.blit(text, text_rect)

# -------------------- LÓGICA DE JOGO E CONEXÃO ----------------------

def set_status(msg: str):
    """
    Atualiza a mensagem de status com proteção de thread.
    """
    global status_text
    with lock:
        status_text = msg

def recv_loop():
    """
    Loop que recebe mensagens do servidor e atualiza estado local.
    Executado em thread separada.
    """
    global role, board, current, game_over, winner, players

    buffer = ""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                set_status("Conexão perdida. Feche e abra de novo.")
                break

            buffer += chunk.decode("utf-8", errors="ignore")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                try:
                    msg = json.loads(line)
                except:
                    continue

                t = msg.get("type")

                if t == "ASSIGN_ROLE":
                    role = msg.get("role", "S")
                    set_status(f"Conectado como: {role}")

                elif t == "STATE":
                    # Atualiza estado local do jogo
                    board = msg.get("board", board)
                    current = msg.get("current", current)
                    game_over = msg.get("game_over", False)
                    winner = msg.get("winner", None)
                    players = msg.get("players", players)

                    # Atualiza mensagem de status dependendo do papel e do jogo
                    if role in ("X", "O"):
                        if game_over:
                            if winner == "EMPATE":
                                set_status("Empate!")
                            elif winner == role:
                                set_status("Você venceu! :)")
                            else:
                                set_status(f"Você perdeu :( Vencedor: {winner}")
                        else:
                            if current == role:
                                set_status("Sua vez! Toque no tabuleiro")
                            else:
                                set_status("Aguardando oponente...")
                    else:
                        set_status("Assistindo..." if players >= 2 else "Aguardando jogadores...")

    except Exception:
        set_status("Erro na conexão.")

def connect(mode: str):
    """
    Conecta ao servidor e inicia thread de recepção de mensagens.
    `mode` = "PLAY" ou "SPECTATE"
    """
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    sock.sendall(serialize_message({"type": "CONNECT", "mode": mode}))
    threading.Thread(target=recv_loop, daemon=True).start()

def send_move(r, c):
    """
    Envia jogada para o servidor.
    Só envia se for a vez do jogador.
    """
    if role in ("X", "O") and not game_over and current == role:
        sock.sendall(serialize_message({"type": "MOVE", "row": r, "col": c}))

def send_restart():
    """
    Solicita reinício do jogo.
    """
    sock.sendall(serialize_message({"type": "RESTART"}))

# -------------------- LOOP PRINCIPAL ----------------------

def main():
    global ui_mode

    clock = pygame.time.Clock()

    while True:
        paint_gradient()

        if ui_mode == "MENU":
            # Título
            title = font_mid.render("JOGO DA VELHA", True, BLACK)
            screen.blit(title, (W//2 - title.get_width()//2, 120))

            # Imagem ou emoji
            if use_img:
                screen.blit(img, (W//2 - img.get_width()//2, 180))
            else:
                emoji = font_big.render("🌸", True, BLACK)
                screen.blit(emoji, (W//2 - emoji.get_width()//2, 180))

            # Botões de menu
            btn_play = button("Jogar", 300)
            btn_watch = button("Assistir", 360)

            # Eventos do menu
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    x, y = ev.pos
                    if btn_play.collidepoint(x, y):
                        ui_mode = "GAME"
                        set_status("Conectando como jogador...")
                        connect("PLAY")
                    elif btn_watch.collidepoint(x, y):
                        ui_mode = "GAME"
                        set_status("Conectando como espectador...")
                        connect("SPECTATE")

        else:
            # Modo de jogo
            draw_board()
            status_line()

            # Botões de jogo
            btn_restart = button("Reiniciar", H - 110)
            btn_menu = button("Menu", H - 60)

            # Eventos do jogo
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    x, y = ev.pos

                    # Clique no tabuleiro
                    if 10 <= x <= 10 + BOARD_H and 10 <= y <= 10 + BOARD_H:
                        c = (x - 10) // CELL
                        r = (y - 10) // CELL
                        send_move(r, c)

                    # Botão reiniciar
                    if btn_restart.collidepoint(x, y):
                        send_restart()
                    # Botão voltar ao menu
                    if btn_menu.collidepoint(x, y):
                        ui_mode = "MENU"
                        try:
                            sock.close()
                        except:
                            pass

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()