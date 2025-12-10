import socket
import threading
import json

from protocol import serialize_message

# Endereço e porta do servidor
HOST = "0.0.0.0"  # Aceita conexões de qualquer IP
PORT = 65432

# Estado global do jogo (compartilhado entre todos os clientes)
BOARD = [[" " for _ in range(3)] for _ in range(3)]  # Tabuleiro 3x3 inicial
CURRENT = "X"          # Quem joga agora ("X" ou "O")
GAME_OVER = False      # Indica se o jogo terminou
WINNER = None          # "X" | "O" | "EMPATE" | None

# Dicionário de clientes conectados
# Estrutura: {thread_id: {"conn": ..., "addr": ..., "role": "X"/"O"/"S"}}
CLIENTS = {}

# Lock para evitar condições de corrida ao acessar/alterar o estado do jogo
LOCK = threading.Lock()

def new_board():
    return [[" " for _ in range(3)] for _ in range(3)] # Cria um novo tabuleiro 3x3 vazio

def build_state():
    # Retorna o estado completo do jogo, que será enviado a todos os clientes (jogadores e espectadores) sempre que houver uma mudança
    return {
        "type": "STATE",
        "board": BOARD,
        "current": CURRENT,
        "game_over": GAME_OVER,
        "winner": WINNER,
        "roles": {tid: c["role"] for tid, c in CLIENTS.items()},  # Papel de cada cliente
        "players": sum(1 for c in CLIENTS.values() if c["role"] in ("X", "O"))  # Contagem de jogadores ativos
    }

def broadcast(msg: dict):
    """
    Envia a mesma mensagem para todos os clientes conectados.
    Remove clientes que desconectarem inesperadamente.
    """
    payload = serialize_message(msg)  # Converte a mensagem para bytes
    dead = []  # Lista de clientes que falharam ao enviar
    for tid, info in CLIENTS.items():
        try:
            info["conn"].sendall(payload)  # Envia a mensagem
        except Exception:
            dead.append(tid)  # Marca cliente como desconectado
    for tid in dead:
        CLIENTS.pop(tid, None)  # Remove clientes mortos

def assign_role(requested: str) -> str:
    """
    Decide o papel do cliente que se conectou.
    Se houver vaga, retorna "X" ou "O".
    Caso contrário, retorna "S" (espectador).
    """
    used = {c["role"] for c in CLIENTS.values()}  # Papéis já ocupados
    if requested == "PLAY":
        if "X" not in used:
            return "X"
        if "O" not in used:
            return "O"
    return "S"  # Se não houver vaga para jogar, será espectador

def reset_if_needed():
    """
    Se não houver dois jogadores conectados, reinicia o jogo
    e volta para o estado inicial.
    """
    global BOARD, CURRENT, GAME_OVER, WINNER
    players = [c for c in CLIENTS.values() if c["role"] in ("X", "O")]
    if len(players) < 2:
        BOARD = new_board()
        CURRENT = "X"
        GAME_OVER = False
        WINNER = None

def check_winner():
    """
    Verifica se alguém venceu ou se houve empate e atualiza
    as variáveis GAME_OVER e WINNER.
    """
    global WINNER, GAME_OVER
    b = BOARD

    # Verifica linhas
    for r in range(3):
        if b[r][0] != " " and b[r][0] == b[r][1] == b[r][2]:
            WINNER = b[r][0]
            GAME_OVER = True
            return

    # Verifica colunas
    for c in range(3):
        if b[0][c] != " " and b[0][c] == b[1][c] == b[2][c]:
            WINNER = b[0][c]
            GAME_OVER = True
            return

    # Verifica diagonais
    if b[0][0] != " " and b[0][0] == b[1][1] == b[2][2]:
        WINNER = b[0][0]
        GAME_OVER = True
        return
    if b[0][2] != " " and b[0][2] == b[1][1] == b[2][0]:
        WINNER = b[0][2]
        GAME_OVER = True
        return

    # Verifica empate (tabuleiro cheio sem vencedor)
    if all(b[r][c] != " " for r in range(3) for c in range(3)):
        WINNER = "EMPATE"
        GAME_OVER = True

def handle_client(conn: socket.socket, addr):
    """
    Função que lida com cada cliente conectado em uma thread separada.
    Recebe mensagens, processa jogadas, atribui papéis e transmite
    o estado atualizado para todos os clientes.
    """
    global BOARD, CURRENT, GAME_OVER, WINNER, CLIENTS

    tid = threading.get_ident()  # ID da thread
    buffer = ""  # Buffer para receber mensagens completas (linha a linha)

    try:
        while True:
            chunk = conn.recv(4096)  # Recebe dados do cliente
            if not chunk:
                break  # Cliente desconectou

            buffer += chunk.decode("utf-8", errors="ignore")

            # Processa mensagens linha por linha
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                msg = json.loads(line)  # Converte JSON em dict
                mtype = msg.get("type")

                if mtype == "CONNECT":
                    # Cliente quer se conectar
                    mode = msg.get("mode", "S")  # "PLAY" ou "S"

                    with LOCK:
                        role = assign_role(mode)  # Decide papel
                        CLIENTS[tid] = {"conn": conn, "addr": addr, "role": role}

                        # Se não houver 2 jogadores, reseta o tabuleiro
                        reset_if_needed()

                    # Envia papel atribuído ao cliente
                    conn.sendall(serialize_message({
                        "type": "ASSIGN_ROLE",
                        "role": role
                    }))

                    # Envia estado atual do jogo
                    conn.sendall(serialize_message(build_state()))
                
                elif mtype == "MOVE":
                    # Jogada de um jogador
                    row, col = msg["row"], msg["col"]
                    with LOCK:
                        me = CLIENTS[tid]["role"]
                        # Só joga se for X ou O, não estiver game over e for sua vez
                        if me in ("X", "O") and not GAME_OVER and me == CURRENT:
                            if BOARD[row][col] == " ":
                                BOARD[row][col] = me
                                check_winner()
                                if not GAME_OVER:
                                    # Alterna jogador
                                    CURRENT = "O" if CURRENT == "X" else "X"
                    # Envia estado atualizado para todos
                    broadcast(build_state())

                elif mtype == "RESTART":
                    # Reinicia o jogo manualmente
                    with LOCK:
                        BOARD = new_board()
                        CURRENT = "X"
                        GAME_OVER = False
                        WINNER = None
                    broadcast(build_state())

    except Exception:
        pass
    finally:
        # Remove cliente da lista ao desconectar e atualiza estado
        with LOCK:
            CLIENTS.pop(tid, None)
            reset_if_needed()
            broadcast(build_state())
        try:
            conn.close()
        except Exception:
            pass

def main():
    """
    Inicializa o servidor TCP e aguarda conexões.
    Cada cliente é tratado em uma thread separada.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Reuso de endereço
        s.bind((HOST, PORT))  # Associa host e porta
        s.listen()  # Começa a escutar conexões
        print(f"Servidor TCP iniciado em {HOST}:{PORT} (aceitando conexões...)")

        while True:
            conn, addr = s.accept()  # Aceita novo cliente
            # Cria thread para tratar o cliente
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()