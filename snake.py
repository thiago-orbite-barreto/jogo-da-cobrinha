"""
Jogo da Cobrinha no terminal
============================

Controles durante uma partida: W/A/S/D ou setas para mover e Q para sair.
O menu, os records e as opções são mantidos em arquivos JSON ao lado deste
arquivo. A renderização fica isolada em `draw`, facilitando uma futura UI
gráfica com tkinter, pygame ou outra biblioteca.
"""

from __future__ import annotations

import json
import os
import random
import select
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_WIDTH = 30
DEFAULT_HEIGHT = 15
TICK_SECONDS = 0.12
SCORE_FILE = Path(__file__).with_name("highscore.json")
SETTINGS_FILE = Path(__file__).with_name("settings.json")
Point = tuple[int, int]


@dataclass
class Record:
    name: str
    score: int
    played_at: str


@dataclass
class Settings:
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    fullscreen: bool = False
    theme: str = "Clássico"


def load_records() -> list[Record]:
    """Carrega todos os resultados e migra o formato antigo de recorde único."""

    try:
        with SCORE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    if isinstance(data, dict):
        # Compatibilidade com a primeira versão, que salvava apenas o recorde.
        if "name" in data and "score" in data:
            return [Record(str(data["name"]), int(data["score"]), "Data não registrada")]
        return []
    if not isinstance(data, list):
        return []

    records: list[Record] = []
    for item in data:
        if isinstance(item, dict) and "name" in item and "score" in item:
            try:
                records.append(
                    Record(
                        str(item["name"]),
                        int(item["score"]),
                        str(item.get("played_at", "Data não registrada")),
                    )
                )
            except (TypeError, ValueError):
                continue
    return records


def save_records(records: list[Record]) -> None:
    with SCORE_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            [
                {"name": record.name, "score": record.score, "played_at": record.played_at}
                for record in records
            ],
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_settings() -> Settings:
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        settings = Settings(
            int(data.get("width", DEFAULT_WIDTH)),
            int(data.get("height", DEFAULT_HEIGHT)),
            bool(data.get("fullscreen", False)),
            str(data.get("theme", "Clássico")),
        )
        if (settings.width, settings.height) not in {(20, 10), (30, 15), (40, 20)}:
            return Settings(theme=settings.theme, fullscreen=settings.fullscreen)
        return settings
    except (FileNotFoundError, json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return Settings()


def save_settings(settings: Settings) -> None:
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(settings.__dict__, file, ensure_ascii=False, indent=2)


def best_record(records: list[Record]) -> Record:
    return max(records, key=lambda record: record.score, default=Record("Ninguém", 0, ""))


def clear_screen() -> None:
    print("\033[2J\033[H", end="")


def hide_cursor() -> None:
    print("\033[?25l", end="")


def show_cursor() -> None:
    print("\033[?25h", end="")


def enter_fullscreen() -> None:
    """Usa o buffer alternativo ANSI para ocupar toda a área do terminal."""

    print("\033[?1049h", end="")


def exit_fullscreen() -> None:
    print("\033[?1049l", end="")


class Keyboard:
    """Leitor de teclas sem bloquear o laço da partida."""

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
        if self._windows:
            import msvcrt

            if not msvcrt.kbhit():
                return None
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                key = msvcrt.getwch()
                return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(key)
            return key.lower()

        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return None
        key = sys.stdin.read(1)
        if key == "\x1b":
            sequence = sys.stdin.read(2)
            return {"\x1b[A": "up", "\x1b[B": "down", "\x1b[D": "left", "\x1b[C": "right"}.get(
                key + sequence
            )
        return key.lower()


def random_food(snake: list[Point], settings: Settings) -> Optional[Point]:
    free_cells = [
        (x, y)
        for y in range(settings.height)
        for x in range(settings.width)
        if (x, y) not in snake
    ]
    return random.choice(free_cells) if free_cells else None


def draw(
    snake: list[Point],
    food: Optional[Point],
    score: int,
    record: Record,
    settings: Settings,
    message: str = "",
) -> None:
    """Renderiza a partida; esta é a principal fronteira para uma futura UI."""

    cells = {(x, y): "o" for x, y in snake}
    if snake:
        cells[snake[0]] = "@"
    if food is not None:
        cells[food] = "*"
    lines = [f"Snake | Pontos: {score} | Recorde: {record.score} ({record.name})"]
    lines.append("+" + "-" * settings.width + "+")
    for y in range(settings.height):
        lines.append("|" + "".join(cells.get((x, y), " ") for x in range(settings.width)) + "|")
    lines.append("+" + "-" * settings.width + "+")
    lines.append("W/A/S/D ou setas para mover | Q para sair")
    if message:
        lines.append(message)
    clear_screen()
    print("\n".join(lines), flush=True)


def ask_player_name() -> str:
    show_cursor()
    while True:
        name = input("\nNovo recorde! Digite seu nome: ").strip()
        if name:
            return name[:30]
        print("O nome não pode ficar vazio.")


def play(record: Record, settings: Settings) -> tuple[int, bool]:
    """Executa uma partida e retorna (pontuação, jogador_saiu)."""

    center = (settings.width // 2, settings.height // 2)
    snake: list[Point] = [center, (center[0] - 1, center[1])]
    direction: Point = (1, 0)
    next_direction = direction
    food = random_food(snake, settings)
    score = 0
    directions = {
        "up": (0, -1), "w": (0, -1), "down": (0, 1), "s": (0, 1),
        "left": (-1, 0), "a": (-1, 0), "right": (1, 0), "d": (1, 0),
    }

    with Keyboard() as keyboard:
        hide_cursor()
        try:
            draw(snake, food, score, record, settings, "Aperte qualquer tecla para iniciar o jogo")
            while keyboard.read_key() is None:
                time.sleep(0.03)
            while True:
                key = keyboard.read_key()
                if key == "q":
                    return score, True
                if key in directions:
                    candidate = directions[key]
                    if candidate != (-direction[0], -direction[1]):
                        next_direction = candidate
                direction = next_direction
                new_head = (snake[0][0] + direction[0], snake[0][1] + direction[1])
                hit_wall = not (0 <= new_head[0] < settings.width and 0 <= new_head[1] < settings.height)
                grows = new_head == food
                if hit_wall or new_head in (snake if grows else snake[:-1]):
                    return score, False
                snake.insert(0, new_head)
                if grows:
                    score += 1
                    food = random_food(snake, settings)
                else:
                    snake.pop()
                draw(snake, food, score, record, settings)
                time.sleep(TICK_SECONDS)
        finally:
            show_cursor()


def show_records(records: list[Record]) -> None:
    clear_screen()
    print("=== RECORDS ===\n")
    if not records:
        print("Nenhuma partida concluída ainda.")
    else:
        print(f"{'#':<4}{'Pontos':<10}{'Jogador':<25}Data")
        print("-" * 62)
        for index, record in enumerate(records, 1):
            print(f"{index:<4}{record.score:<10}{record.name[:23]:<25}{record.played_at}")
    input("\nPressione ENTER para voltar ao menu...")


def show_graphics_options(settings: Settings) -> None:
    clear_screen()
    print("=== GRÁFICOS SIMPLES ===\n")
    print("1. ASCII (atual) - compatível com qualquer terminal; simples de manter.")
    print("2. Unicode - permite blocos e símbolos mais bonitos; pode falhar em terminais antigos.")
    print("3. Cores ANSI - melhora a leitura; depende do suporte de cores do terminal.")
    print("\nEvolução futura: separar sprites, paleta e efeitos da lógica do jogo.")
    print("Assim, tkinter pode oferecer menus nativos ou pygame pode adicionar animações.")
    print(f"\nTema preparado: {settings.theme} (mudança de temas será adicionada futuramente).")
    input("\nPressione ENTER para voltar...")


def options_menu(settings: Settings) -> None:
    while True:
        clear_screen()
        fullscreen = "Ligado" if settings.fullscreen else "Desligado"
        print("=== OPÇÕES ===\n")
        print(f"1. Resolução: {settings.width}x{settings.height}")
        print(f"2. Tela cheia: {fullscreen} (usa toda a área do terminal)")
        print("3. Gráficos simples e planos para o futuro")
        print("4. Voltar")
        choice = input("\nEscolha uma opção: ").strip()
        if choice == "1":
            clear_screen()
            print("=== RESOLUÇÃO ===\n1. Pequena (20x10)\n2. Padrão (30x15)\n3. Grande (40x20)")
            resolution = input("\nEscolha: ").strip()
            sizes = {"1": (20, 10), "2": (30, 15), "3": (40, 20)}
            if resolution in sizes:
                settings.width, settings.height = sizes[resolution]
                save_settings(settings)
        elif choice == "2":
            settings.fullscreen = not settings.fullscreen
            save_settings(settings)
        elif choice == "3":
            show_graphics_options(settings)
        elif choice == "4":
            return


def start_game(records: list[Record], settings: Settings) -> None:
    record = best_record(records)
    score, quit_requested = play(record, settings)
    if quit_requested:
        records.insert(0, Record("Jogador", score, datetime.now().strftime("%d/%m/%Y %H:%M")))
        save_records(records)
        return
    clear_screen()
    print(f"Fim de jogo! Você fez {score} ponto(s).")
    name = ask_player_name() if score > record.score else "Jogador"
    records.insert(0, Record(name, score, datetime.now().strftime("%d/%m/%Y %H:%M")))
    save_records(records)
    print("Resultado salvo nos Records.")
    input("\nPressione ENTER para voltar ao menu...")


def main() -> None:
    records = load_records()
    settings = load_settings()
    if settings.fullscreen:
        enter_fullscreen()
    try:
        while True:
            clear_screen()
            record = best_record(records)
            print("=== JOGO DA COBRINHA ===\n")
            print("1. Iniciar jogo")
            print("2. Records")
            print("3. Opções")
            print("4. Sair")
            print(f"\nMelhor resultado: {record.score} pontos ({record.name})")
            choice = input("\nEscolha uma opção: ").strip()
            if choice == "1":
                start_game(records, settings)
            elif choice == "2":
                show_records(records)
            elif choice == "3":
                was_fullscreen = settings.fullscreen
                options_menu(settings)
                if settings.fullscreen != was_fullscreen:
                    (enter_fullscreen if settings.fullscreen else exit_fullscreen)()
            elif choice == "4":
                clear_screen()
                print("Jogo encerrado.")
                return
    finally:
        if settings.fullscreen:
            exit_fullscreen()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        show_cursor()
        print("\nJogo encerrado.")
