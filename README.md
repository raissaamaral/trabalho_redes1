# 🌸 Jogo da Velha TCP – Cliente/Servidor 🌸

Este projeto implementa um **Jogo da Velha** multiplayer utilizando arquitetura cliente-servidor com comunicação **TCP** para garantir a confiabilidade e ordem das jogadas.

**Discentes:**
* Raíssa Santos Amaral Moreira (202220037)
* Adrielle Maria Alves Queiroz (202220184)


## 1. Descrição Geral

Este sistema é um Jogo da Velha (Tic-Tac-Toe) com as seguintes funcionalidades:

* Dois jogadores ativos (**X** e **O**).
* Suporte para conexões extras como **espectadores** (**S**).
* Interface gráfica interativa desenvolvida com **Pygame**.
* Estado do jogo sincronizado em **tempo real** para todos os clientes.


## 2. Arquitetura do Sistema 

A solução é dividida em três componentes principais, que se comunicam através de Sockets TCP:

### 2.1. `server_tcp.py` (Servidor)
* Gerencia todas as conexões de clientes.
* Define os papéis dos clientes (X, O, Espectador).
* Mantém o estado global do tabuleiro.
* Valida as jogadas recebidas.
* Envia atualizações de estado para todos os clientes conectados.

### 2.2. `client_tcp.py` (Cliente)
* Responsável pela Interface Gráfica (GUI) do jogo.
* Apresenta menu de escolha: **Jogar** ou **Assistir**.
* Renderiza o tabuleiro, botões e barra de status.
* Utiliza uma thread dedicada para receber mensagens do servidor em tempo real.

### 2.3. `protocol.py` (Protocolo)
* Biblioteca para serialização e desserialização de mensagens.
* Utiliza o formato **JSON** para estruturar os dados.
* Inclui a função `serialize_message()` para preparar o envio.


## 3. Protocolo de Aplicação

### 3.1. Formato Geral
* Dados transmitidos em formato **JSON**.
* Codificação **UTF-8**.
* Cada mensagem é encerrada com o caractere de nova linha (`\n`).

### 3.2. Tipos de Mensagem

| Tipo | Enviado por | Função |
| :---: | :---: | :--- |
| **CONNECT** | Cliente | Solicita entrada no servidor, definindo o modo (PLAY/SPECTATE). |
| **ASSIGN\_ROLE** | Servidor | Define o papel do cliente (X, O ou S). |
| **MOVE** | Cliente | Envia a jogada do cliente (linha e coluna). |
| **STATE** | Servidor | Envia o estado completo e atualizado do jogo (tabuleiro, turno, fim de jogo). |
| **RESTART** | Cliente | Solicita ao servidor o reinício de uma nova partida. |

### 3.3. Exemplos de Mensagens

| Tipo | Exemplo JSON |
| :---: | :--- |
| **CONNECT** | `{ "type": "CONNECT", "mode": "PLAY" }` |
| **MOVE** | `{ "type": "MOVE", "row": 1, "col": 2 }` |
| **STATE** | `{ "type": "STATE", "board": [...], "current": "X", "game_over": false }` |
| **RESTART** | `{ "type": "RESTART" }` |


## 4. Motivação da Escolha do TCP

O protocolo TCP (Transmission Control Protocol) foi escolhido para garantir a integridade da experiência do jogo:

* **Entrega Confiável:** Garante que todas as jogadas cheguem ao destino.
* **Ordem Garantida:** As mensagens são recebidas na mesma sequência em que foram enviadas.
* **Zero Perda de Pacotes:** Evita que jogadas importantes sejam perdidas.
* **Estado Consistente:** Mantém o tabuleiro sincronizado e evita erros graves no fluxo do jogo.


## 5. Como Executar
* **5.1. Instalar Dependências**
    ```bash
    pip install pygame
    ```

* **5.2. Iniciar Servidor e Cliente**
    ```bash
    python server_tcp.py
    python client_tcp.py
    ```
    > **Observação:** Abra dois clientes para jogar ativamente e quantos quiser para assistir como espectadores.

    1) No PC 2 (ou em outro computador que irá se conectar), abra o terminal e digite ipconfig.
    2) Localize o endereço IPv4 da sua rede Wi-Fi.
    3) Execute o cliente passando o IP do servidor, por exemplo:
     ```bash
    python client_tcp.py 192.168.x.x
    ```


## 6. Estrutura de arquivos
```.
├── client_tcp.py
├── flor.png
├── protocol.py
├── README.md
└── server_tcp.py
```

## 
**Projeto da disciplina Redes de Computadores 1 - 2025.2** 