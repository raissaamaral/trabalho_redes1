import json

DELIM = "\n"  # Delimitador de fim de mensagem

def serialize_message(data: dict) -> bytes:
    """Converte dict em JSON + delimitador para enviar via TCP."""
    return (json.dumps(data) + DELIM).encode("utf-8")

def recv_messages(sock) -> list[dict]:
    """
    Ideia: acumular bytes recebidos em um buffer e usar '\n' para separar mensagens JSON completas.
    Não implementada; serve só como documentação do padrão de framing.
    """
    raise NotImplementedError