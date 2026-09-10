"""Jogo da cobrinha com interface gráfica Tkinter."""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Optional

DEFAULT_WIDTH = 30
DEFAULT_HEIGHT = 15
TICK_MS = 120
SCORE_FILE = Path(__file__).with_name("highscore.json")
SETTINGS_FILE = Path(__file__).with_name("settings.json")
Point = tuple[int, int]
MENU_MUSIC_FILE = Path(__file__).with_name("menu_theme.mp3")


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
    try:
        data = json.loads(SCORE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    if isinstance(data, dict) and "name" in data and "score" in data:
        data = [{"name": data["name"], "score": data["score"], "played_at": "Data não registrada"}]
    if not isinstance(data, list):
        return []
    records = []
    for item in data:
        if isinstance(item, dict) and "name" in item and "score" in item:
            try:
                records.append(Record(str(item["name"]), int(item["score"]), str(item.get("played_at", ""))))
            except (TypeError, ValueError):
                continue
    return records


def save_records(records: list[Record]) -> None:
    SCORE_FILE.write_text(
        json.dumps([record.__dict__ for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_settings() -> Settings:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
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
    SETTINGS_FILE.write_text(json.dumps(settings.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")


def best_record(records: list[Record]) -> Record:
    return max(records, key=lambda record: record.score, default=Record("Ninguém", 0, ""))


class AudioPlayer:
    """Reproduz a música do menu sem exigir dependências externas."""

    def __init__(self, file: Path) -> None:
        self.file = file
        self.process: Optional[subprocess.Popen[bytes]] = None
        self.alias = "snake_menu_theme"

    def play_loop(self) -> None:
        if not self.file.exists():
            return
        if os.name == "nt":
            import ctypes

            command = f'open "{self.file}" type mpegvideo alias {self.alias}'
            ctypes.windll.winmm.mciSendStringW(command, None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f"play {self.alias} repeat", None, 0, None)
            return
        player = "afplay" if sys.platform == "darwin" else "ffplay"
        try:
            arguments = [player, "-nodisp", "-autoexit", str(self.file)]
            if player == "ffplay":
                arguments[1:1] = ["-loglevel", "quiet", "-loop", "0"]
            self.process = subprocess.Popen(arguments)
        except FileNotFoundError:
            self.process = None

    def stop(self) -> None:
        if os.name == "nt":
            import ctypes

            ctypes.windll.winmm.mciSendStringW(f"stop {self.alias}", None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f"close {self.alias}", None, 0, None)
        elif self.process is not None:
            self.process.terminate()
            self.process = None


class SnakeApp:
    """Janela principal, menus e partida do jogo."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.records = load_records()
        self.settings = load_settings()
        self.cell_size = 24
        self.snake: list[Point] = []
        self.food: Optional[Point] = None
        self.direction: Point = (1, 0)
        self.next_direction: Point = self.direction
        self.score = 0
        self.game_running = False
        self.game_started = False
        self.game_after_id: Optional[str] = None
        self.audio = AudioPlayer(MENU_MUSIC_FILE)
        self.root.title("Jogo da Cobrinha")
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
        self.root.bind("<KeyPress>", self.on_key)
        self.apply_window_settings()
        self.audio.play_loop()
        self.show_menu()

    def apply_window_settings(self) -> None:
        self.root.attributes("-fullscreen", self.settings.fullscreen)
        if not self.settings.fullscreen:
            self.root.geometry(f"{self.settings.width * self.cell_size + 40}x{self.settings.height * self.cell_size + 150}")

    def clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def show_menu(self) -> None:
        self.clear()
        self.menu_canvas = tk.Canvas(
            self.root, bg="#090d1c", highlightthickness=0,
            width=620, height=520,
        )
        self.menu_canvas.pack(fill="both", expand=True)
        self.menu_items = ("Iniciar jogo", "Records", "Opções", "Sair")
        self.menu_index = 0
        self.menu_canvas.bind("<KeyPress>", self.on_menu_key)
        self.menu_canvas.focus_set()
        self.menu_canvas.create_text(310, 105, text="SNAKE", fill="#69b7e8", font=("Times New Roman", 42, "bold"))
        self.menu_canvas.create_text(310, 150, text="THE QUIET HOUR", fill="#dce9f2", font=("Times New Roman", 18, "bold"))
        self.menu_canvas.create_line(160, 175, 460, 175, fill="#31577a", width=2)
        self.menu_canvas.create_text(310, 205, text="Uma aventura em escamas", fill="#7f9ab0", font=("Arial", 11, "italic"))
        self.menu_canvas.bind("<Button-1>", self.on_menu_click)
        self.render_menu_items()
        record = best_record(self.records)
        self.menu_canvas.create_text(310, 435, text=f"Melhor resultado: {record.score} pontos ({record.name})", fill="#91a8bc", font=("Arial", 10))
        self.menu_canvas.create_text(310, 475, text="↑ ↓ navegar     ENTER selecionar     ESC sair", fill="#526b80", font=("Arial", 9))

    def render_menu_items(self) -> None:
        self.menu_canvas.delete("menu_item")
        for index, item in enumerate(self.menu_items):
            y = 270 + index * 36
            selected = index == self.menu_index
            color = "#f4c95d" if selected else "#d6e1e8"
            prefix = "▶  " if selected else "   "
            self.menu_canvas.create_text(310, y, text=prefix + item, fill=color, font=("Arial", 15, "bold" if selected else "normal"), tags="menu_item")

    def on_menu_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key in ("up", "w"):
            self.menu_index = (self.menu_index - 1) % len(self.menu_items)
            self.render_menu_items()
        elif key in ("down", "s"):
            self.menu_index = (self.menu_index + 1) % len(self.menu_items)
            self.render_menu_items()
        elif key in ("return", "space"):
            self.select_menu_item()
        elif key == "escape":
            self.close_app()

    def on_menu_click(self, event: tk.Event) -> None:
        index = round((event.y - 270) / 36)
        if 0 <= index < len(self.menu_items):
            self.menu_index = index
            self.select_menu_item()

    def select_menu_item(self) -> None:
        actions = (self.start_game, self.show_records, self.show_options, self.close_app)
        actions[self.menu_index]()

    def close_app(self) -> None:
        self.audio.stop()
        self.root.destroy()

    def show_records(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=25)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="RECORDS", font=("Arial", 20, "bold")).pack(pady=(0, 15))
        tree = ttk.Treeview(frame, columns=("score", "name", "date"), show="headings", height=12)
        for column, title in (("score", "Pontos"), ("name", "Jogador"), ("date", "Data")):
            tree.heading(column, text=title)
        tree.column("score", width=80, anchor="center")
        tree.column("name", width=220)
        tree.column("date", width=150)
        ranked_records = sorted(
            self.records,
            key=lambda record: (record.score, record.played_at),
            reverse=True,
        )
        for record in ranked_records:
            tree.insert("", "end", values=(record.score, record.name, record.played_at))
        tree.pack(fill="both", expand=True)
        ttk.Button(frame, text="Voltar", command=self.show_menu).pack(pady=(15, 0))

    def show_options(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=25)
        frame.pack(expand=True)
        ttk.Label(frame, text="OPÇÕES", font=("Arial", 20, "bold")).pack(pady=(0, 15))
        ttk.Label(frame, text="Resolução").pack(anchor="w")
        resolution = tk.StringVar(value=f"{self.settings.width}x{self.settings.height}")
        ttk.Combobox(frame, textvariable=resolution, values=("20x10", "30x15", "40x20"), state="readonly").pack(fill="x", pady=5)
        fullscreen = tk.BooleanVar(value=self.settings.fullscreen)
        ttk.Checkbutton(frame, text="Abrir em tela cheia", variable=fullscreen).pack(anchor="w", pady=8)
        ttk.Label(frame, text="Tema: Clássico (preparado para futuras opções)", foreground="#555").pack(pady=8)
        ttk.Button(frame, text="Gráficos simples", command=self.show_graphics).pack(fill="x", pady=5)

        def save_and_return() -> None:
            self.settings.width, self.settings.height = map(int, resolution.get().split("x"))
            self.settings.fullscreen = fullscreen.get()
            save_settings(self.settings)
            self.apply_window_settings()
            self.show_menu()

        ttk.Button(frame, text="Salvar e voltar", command=save_and_return).pack(fill="x", pady=5)
        ttk.Button(frame, text="Voltar sem salvar", command=self.show_menu).pack(fill="x", pady=5)

    def show_graphics(self) -> None:
        messagebox.showinfo(
            "Gráficos simples",
            "ASCII: máxima compatibilidade e manutenção simples.\n\n"
            "Unicode: símbolos mais bonitos, mas depende da fonte do sistema.\n\n"
            "Cores: melhor leitura e feedback, mas depende do suporte visual.\n\n"
            "A evolução pode separar sprites, paleta, animações e efeitos da "
            "lógica atual, usando Canvas, tkinter ou pygame.",
        )

    def start_game(self) -> None:
        self.clear()
        self.canvas = tk.Canvas(
            self.root,
            width=self.settings.width * self.cell_size,
            height=self.settings.height * self.cell_size,
            bg="#102018",
            highlightthickness=0,
        )
        self.canvas.pack(padx=20, pady=(20, 5))
        self.status = ttk.Label(self.root)
        self.status.pack()
        ttk.Label(self.root, text="Setas ou W/A/S/D para mover | Q para sair").pack(pady=(2, 15))
        center = (self.settings.width // 2, self.settings.height // 2)
        self.snake = [center, (center[0] - 1, center[1])]
        self.food = self.random_food()
        self.direction = self.next_direction = (1, 0)
        self.score = 0
        self.game_running = True
        self.game_started = False
        self.draw_game("Aperte qualquer tecla para iniciar o jogo")

    def random_food(self) -> Optional[Point]:
        available = [
            (x, y)
            for y in range(self.settings.height)
            for x in range(self.settings.width)
            if (x, y) not in self.snake
        ]
        return random.choice(available) if available else None

    def draw_game(self, message: str = "") -> None:
        self.canvas.delete("all")
        for x, y in self.snake:
            color = "#7ee787" if (x, y) == self.snake[0] else "#3fb950"
            self.canvas.create_rectangle(x * self.cell_size, y * self.cell_size, (x + 1) * self.cell_size, (y + 1) * self.cell_size, fill=color, outline="#102018")
        if self.food:
            x, y = self.food
            self.canvas.create_oval(x * self.cell_size + 4, y * self.cell_size + 4, (x + 1) * self.cell_size - 4, (y + 1) * self.cell_size - 4, fill="#ff6b6b", outline="")
        record = best_record(self.records)
        self.status.configure(text=f"Pontos: {self.score}    Recorde: {record.score} ({record.name})    {message}")

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if not self.game_running:
            return
        if not self.game_started:
            self.game_started = True
            self.tick()
            return
        directions = {"up": (0, -1), "w": (0, -1), "down": (0, 1), "s": (0, 1), "left": (-1, 0), "a": (-1, 0), "right": (1, 0), "d": (1, 0)}
        if key == "q":
            self.end_game(self.score, True)
        elif key in directions:
            candidate = directions[key]
            if candidate != (-self.direction[0], -self.direction[1]):
                self.next_direction = candidate

    def tick(self) -> None:
        if not self.game_running:
            return
        self.direction = self.next_direction
        new_head = (self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1])
        grows = new_head == self.food
        if not (0 <= new_head[0] < self.settings.width and 0 <= new_head[1] < self.settings.height) or new_head in (self.snake if grows else self.snake[:-1]):
            self.end_game(self.score, False)
            return
        self.snake.insert(0, new_head)
        if grows:
            self.score += 1
            self.food = self.random_food()
        else:
            self.snake.pop()
        self.draw_game()
        self.game_after_id = self.root.after(TICK_MS, self.tick)

    def end_game(self, score: int, quit_requested: bool) -> None:
        self.game_running = False
        if self.game_after_id:
            self.root.after_cancel(self.game_after_id)
        if quit_requested:
            self.show_menu()
            return
        previous_best = best_record(self.records).score
        name = simpledialog.askstring("Partida encerrada", f"Você fez {score} ponto(s).\nDigite o nome do jogador:", parent=self.root)
        if not name or not name.strip():
            name = "Jogador"
        record = Record(name.strip()[:30], score, datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.records.insert(0, record)
        save_records(self.records)
        if score > previous_best:
            messagebox.showinfo("Parabéns!", f"Parabéns, {record.name}! Você estabeleceu um novo recorde de {score} pontos!", parent=self.root)
        self.show_menu()


def main() -> None:
    root = tk.Tk()
    SnakeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
