"""
Jogo da Cobrinha no terminal
============================

Uma implementação pequena e didática de Snake usando apenas a biblioteca
 padrão do Python. O programa foi organizado em partes independentes para que
 a interface de terminal possa ser trocada futuramente por uma UI gráfica.

Controles:
    W/A/S/D ou setas  - mover
    Q                - sair

O recorde fica salvo em "highscore.json", ao lado deste arquivo.
"""

from __future__ import annotations

import json
import os
import random
import select
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


WIDTH = 30
HEIGHT = 15
TICK_SECONDS = 0.12
SCORE_FILE = Path(__file__).with_name("highscore.json")

Point = tuple[int, int]


@dataclass
class HighScore:
    """Representa o melhor resultado conhecido."""

    name: str = "Ninguém"
    score: int = 0


def load_high_score() -> HighScore:
    """Lê o recorde do JSON; se ele ainda não existir, começa do zero."""

    try:
        with SCORE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return HighScore(str(data["name"]), int(data["score"]))
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Um arquivo ausente ou inválido não impede o jogo de funcionar.
        return HighScore()


def save_high_score(high_score: HighScore) -> None:
    """Salva o recorde em formato legível para facilitar estudos."""

    with SCORE_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            {"name": high_score.name, "score": high_score.score},
            file,
            ensure_ascii=False,
            indent=2,
        )


def clear_screen() -> None:
    """Limpa a tela usando ANSI (compatível com terminais modernos)."""

    print("\033[2J\033[H", end="")


def hide_cursor() -> None:
    print("\033[?25l", end="")


def show_cursor() -> None:
    print("\033[?25h", end="")


class Keyboard:
    """
    Leitor de teclado sem bloquear o jogo.

    No Windows, msvcrt lê teclas imediatamente. Em Linux/macOS, o terminal
    entra temporariamente em modo "raw" e select() verifica se há entrada.
    """

    def __init__(self) -> None:
        self._windows = os.name == "nt"
        self._old_terminal = None

    def __enter__(self) -> "Keyboard":
        if not self._windows:
            import termios
            import tty

            self._old_terminal = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, *_args: object) -> None:
        if not self._windows and self._old_terminal is not None:
            import termios

            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_terminal)

    def read_key(self) -> Optional[str]:
        """Retorna uma tecla ou None quando nenhuma tecla foi pressionada."""

        if self._windows:
            import msvcrt

            if not msvcrt.kbhit():
                return None
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):  # Prefixo de teclas especiais no Windows.
                key = msvcrt.getwch()
                return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(
                    key
                )
            return key.lower()

        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return None
        key = sys.stdin.read(1)
        if key == "\x1b":  # Sequência ANSI das setas: ESC [ A/B/C/D.
            sequence = sys.stdin.read(2)
            return {"\x1b[A": "up", "\x1b[B": "down", "\x1b[D": "left", "\x1b[C": "right"}.get(
                key + sequence
            )
        return key.lower()


def random_food(snake: list[Point]) -> Optional[Point]:
    """Escolhe uma posição livre para a comida, se ainda houver alguma."""

    free_cells = [
        (x, y)
        for y in range(HEIGHT)
        for x in range(WIDTH)
        if (x, y) not in snake
    ]
    return random.choice(free_cells) if free_cells else None


def draw(snake: list[Point], food: Optional[Point], score: int, high_score: HighScore) -> None:
    """Desenha uma nova moldura completa; esta função é o ponto de troca da UI."""

    cells = {(x, y): "o" for x, y in snake}
    if snake:
        cells[snake[0]] = "@"
    if food is not None:
        cells[food] = "*"

    lines = [f"Snake | Pontos: {score} | Recorde: {high_score.score} ({high_score.name})"]
    lines.append("+" + "-" * WIDTH + "+")
    for y in range(HEIGHT):
        lines.append("|" + "".join(cells.get((x, y), " ") for x in range(WIDTH)) + "|")
    lines.append("+" + "-" * WIDTH + "+")
    lines.append("W/A/S/D ou setas para mover | Q para sair")
    clear_screen()
    print("\n".join(lines), flush=True)


def ask_player_name() -> str:
    """Solicita e normaliza o nome usado no registro do recorde."""

    show_cursor()
    while True:
        name = input("\nNovo recorde! Digite seu nome: ").strip()
        if name:
            return name[:30]
        print("O nome não pode ficar vazio.")


def play(high_score: HighScore) -> tuple[int, bool]:
    """Executa uma partida e retorna (pontuação, jogador_saiu)."""

    snake: list[Point] = [(WIDTH // 2, HEIGHT // 2), (WIDTH // 2 - 1, HEIGHT // 2)]
    direction: Point = (1, 0)
    next_direction = direction
    food = random_food(snake)
    score = 0

    with Keyboard() as keyboard:
        hide_cursor()
        try:
            while True:
                key = keyboard.read_key()
                directions = {
                    "up": (0, -1), "w": (0, -1),
                    "down": (0, 1), "s": (0, 1),
                    "left": (-1, 0), "a": (-1, 0),
                    "right": (1, 0), "d": (1, 0),
                }
                if key == "q":
                    return score, True
                if key in directions:
                    candidate = directions[key]
                    # Impede a cobra de inverter e colidir consigo mesma.
                    if candidate != (-direction[0], -direction[1]):
                        next_direction = candidate

                direction = next_direction
                head_x, head_y = snake[0]
                new_head = (head_x + direction[0], head_y + direction[1])

                hit_wall = not (0 <= new_head[0] < WIDTH and 0 <= new_head[1] < HEIGHT)
                grows = new_head == food
                body_to_check = snake if grows else snake[:-1]
                if hit_wall or new_head in body_to_check:
                    return score, False

                snake.insert(0, new_head)
                if grows:
                    score += 1
                    food = random_food(snake)
                else:
                    snake.pop()

                draw(snake, food, score, high_score)
                time.sleep(TICK_SECONDS)
        finally:
            show_cursor()


def main() -> None:
    """Controla o ciclo de partidas e a atualização do recorde."""

    high_score = load_high_score()
    clear_screen()
    print("=== JOGO DA COBRINHA ===")
    print(f"Recorde atual: {high_score.score} pontos por {high_score.name}")
    input("Pressione ENTER para começar...")

    while True:
        score, quit_requested = play(high_score)
        clear_screen()
        if quit_requested:
            print("Jogo encerrado.")
            break

        print(f"Fim de jogo! Você fez {score} ponto(s).")
        if score > high_score.score:
            high_score = HighScore(ask_player_name(), score)
            save_high_score(high_score)
            print(f"Recorde salvo: {high_score.score} pontos por {high_score.name}.")
        else:
            print(f"Recorde continua sendo {high_score.score} pontos por {high_score.name}.")

        answer = input("\nJogar novamente? [s/N]: ").strip().lower()
        if answer != "s":
            break

    show_cursor()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        show_cursor()
        print("\nJogo encerrado.")
