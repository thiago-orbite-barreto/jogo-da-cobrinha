"""Jogo da Cobrinha com UI unificada em Pygame."""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pygame

DEFAULT_WIDTH = 30
DEFAULT_HEIGHT = 15
CELL_SIZE = 24
TICK_MS = 120
SCORE_FILE = Path(__file__).with_name("highscore.json")
SETTINGS_FILE = Path(__file__).with_name("settings.json")
MENU_MUSIC_FILE = Path(__file__).with_name("menu_theme.mp3")
Point = tuple[int, int]

NAVY = (9, 13, 28)
PANEL = (18, 29, 49)
BLUE = (105, 183, 232)
TEXT = (214, 225, 232)
MUTED = (127, 154, 176)
GOLD = (244, 201, 93)
GREEN = (63, 185, 80)
RED = (255, 107, 107)


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
    SCORE_FILE.write_text(json.dumps([record.__dict__ for record in records], ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings() -> Settings:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        settings = Settings(int(data.get("width", DEFAULT_WIDTH)), int(data.get("height", DEFAULT_HEIGHT)), bool(data.get("fullscreen", False)), str(data.get("theme", "Clássico")))
        if (settings.width, settings.height) not in {(20, 10), (30, 15), (40, 20)}:
            return Settings(fullscreen=settings.fullscreen, theme=settings.theme)
        return settings
    except (FileNotFoundError, json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return Settings()


def save_settings(settings: Settings) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")


def best_record(records: list[Record]) -> Record:
    return max(records, key=lambda item: item.score, default=Record("Ninguém", 0, ""))


class SnakeGame:
    def __init__(self) -> None:
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        self.settings = load_settings()
        flags = pygame.FULLSCREEN if self.settings.fullscreen else 0
        self.screen = pygame.display.set_mode(self.window_size(), flags)
        pygame.display.set_caption("Jogo da Cobrinha")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.title_font = pygame.font.Font(None, 54)
        self.small_font = pygame.font.Font(None, 21)
        self.records = load_records()
        self.state = "menu"
        self.menu_index = 0
        self.running = True
        self.music_playing = False
        self.start_menu_music()

    def window_size(self) -> tuple[int, int]:
        return (self.settings.width * CELL_SIZE + 40, self.settings.height * CELL_SIZE + 150)

    def start_menu_music(self) -> None:
        if MENU_MUSIC_FILE.exists() and not self.music_playing:
            try:
                if not pygame.mixer.get_init():
                    return
                pygame.mixer.music.load(str(MENU_MUSIC_FILE))
                pygame.mixer.music.play(-1)
                self.music_playing = True
            except pygame.error:
                self.music_playing = False

    def stop_menu_music(self) -> None:
        if self.music_playing:
            pygame.mixer.music.stop()
            self.music_playing = False

    def draw_text(self, text: str, position: tuple[int, int], font: pygame.font.Font, color: tuple[int, int, int] = TEXT, center: bool = True) -> None:
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        rect.center = position if center else (position[0] + rect.width // 2, position[1] + rect.height // 2)
        if not center:
            rect.topleft = position
        self.screen.blit(surface, rect)

    def draw_header(self, title: str) -> None:
        self.screen.fill(NAVY)
        self.draw_text(title, (self.screen.get_width() // 2, 72), self.title_font, BLUE)
        pygame.draw.line(self.screen, (49, 87, 122), (self.screen.get_width() // 2 - 150, 105), (self.screen.get_width() // 2 + 150, 105), 2)

    def draw_menu(self) -> None:
        self.draw_header("Jogo da Cobrinha")
        items = ("Iniciar jogo", "Records", "Opções", "Sair")
        for index, item in enumerate(items):
            color = GOLD if index == self.menu_index else TEXT
            y = 180 + index * 43
            self.draw_text(item, (self.screen.get_width() // 2, y), self.font, color)
            if index == self.menu_index:
                self.draw_glove((self.screen.get_width() // 2 - 150, y))
        record = best_record(self.records)
        self.draw_text(f"Melhor resultado: {record.score} pontos ({record.name})", (self.screen.get_width() // 2, self.screen.get_height() - 55), self.small_font, MUTED)
        self.draw_text("W/S navegar     ENTER selecionar     ESC sair", (self.screen.get_width() // 2, self.screen.get_height() - 25), self.small_font, (82, 107, 128))

    def draw_glove(self, position: tuple[int, int]) -> None:
        """Desenha o seletor como uma luvinha, sem depender de glifos Unicode."""

        x, y = position
        outline = (30, 38, 48)
        glove = (238, 238, 214)
        shadow = (174, 181, 177)
        # Silhueta de uma mao apontando para a opcao selecionada.
        hand = (
            (x - 27, y - 4), (x - 16, y - 12), (x - 16, y - 25),
            (x - 11, y - 28), (x - 7, y - 25), (x - 7, y - 13),
            (x - 3, y - 13), (x - 3, y - 31), (x + 2, y - 34),
            (x + 7, y - 31), (x + 7, y - 13), (x + 11, y - 13),
            (x + 11, y - 26), (x + 16, y - 28), (x + 21, y - 24),
            (x + 21, y - 5), (x + 14, y + 8), (x + 1, y + 14),
            (x - 14, y + 11),
        )
        pygame.draw.polygon(self.screen, outline, hand)
        inner_hand = tuple((point[0], point[1] + 2) for point in hand)
        pygame.draw.polygon(self.screen, glove, inner_hand)
        pygame.draw.line(self.screen, shadow, (x - 10, y + 7), (x + 10, y + 7), 2)

    def draw_records(self) -> None:
        self.draw_header("Records")
        ranked = sorted(self.records, key=lambda item: (item.score, item.played_at), reverse=True)
        self.draw_text("PONTOS", (self.screen.get_width() // 2 - 160, 135), self.small_font, MUTED)
        self.draw_text("JOGADOR", (self.screen.get_width() // 2 - 35, 135), self.small_font, MUTED)
        self.draw_text("DATA", (self.screen.get_width() // 2 + 150, 135), self.small_font, MUTED)
        for index, record in enumerate(ranked[:10]):
            y = 170 + index * 30
            self.draw_text(f"{record.score}", (self.screen.get_width() // 2 - 160, y), self.font, GOLD)
            self.draw_text(record.name[:20], (self.screen.get_width() // 2 - 35, y), self.small_font)
            self.draw_text(record.played_at, (self.screen.get_width() // 2 + 150, y), self.small_font, MUTED)
        if not ranked:
            self.draw_text("Nenhuma partida registrada.", (self.screen.get_width() // 2, 220), self.font, MUTED)
        self.draw_text("ESC ou ENTER para voltar", (self.screen.get_width() // 2, self.screen.get_height() - 35), self.small_font, MUTED)

    def draw_options(self) -> None:
        self.draw_header("Opções")
        values = (f"Resolução: {self.settings.width}x{self.settings.height}", f"Tela cheia: {'Ligada' if self.settings.fullscreen else 'Desligada'}", "Tema: Clássico (futuro)")
        for index, value in enumerate(values):
            color = GOLD if index == self.menu_index else TEXT
            self.draw_text(value, (self.screen.get_width() // 2, 180 + index * 48), self.font, color)
        self.draw_text("ENTER altera     ESC volta", (self.screen.get_width() // 2, self.screen.get_height() - 35), self.small_font, MUTED)

    def new_game(self) -> None:
        self.stop_menu_music()
        center = (self.settings.width // 2, self.settings.height // 2)
        self.snake = [center, (center[0] - 1, center[1])]
        self.food = self.random_food()
        self.direction = self.next_direction = (1, 0)
        self.score = 0
        self.game_started = False
        self.last_tick = pygame.time.get_ticks()
        self.state = "game"

    def random_food(self) -> Optional[Point]:
        free = [(x, y) for y in range(self.settings.height) for x in range(self.settings.width) if (x, y) not in self.snake]
        return random.choice(free) if free else None

    def draw_game(self) -> None:
        self.screen.fill((16, 32, 24))
        offset_x, offset_y = 20, 55
        for x, y in self.snake:
            color = (126, 231, 135) if (x, y) == self.snake[0] else GREEN
            pygame.draw.rect(self.screen, color, (offset_x + x * CELL_SIZE, offset_y + y * CELL_SIZE, CELL_SIZE - 2, CELL_SIZE - 2))
        if self.food:
            x, y = self.food
            pygame.draw.circle(self.screen, RED, (offset_x + x * CELL_SIZE + CELL_SIZE // 2, offset_y + y * CELL_SIZE + CELL_SIZE // 2), CELL_SIZE // 2 - 4)
        record = best_record(self.records)
        message = "Aperte qualquer tecla para iniciar o jogo" if not self.game_started else f"Pontos: {self.score} | Recorde: {record.score} ({record.name})"
        self.draw_text(message, (self.screen.get_width() // 2, 30), self.small_font, GOLD if not self.game_started else TEXT)
        self.draw_text("Setas ou W/A/S/D para mover | Q para sair", (self.screen.get_width() // 2, self.screen.get_height() - 20), self.small_font, MUTED)

    def move(self) -> None:
        self.direction = self.next_direction
        head = (self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1])
        grows = head == self.food
        if not (0 <= head[0] < self.settings.width and 0 <= head[1] < self.settings.height) or head in (self.snake if grows else self.snake[:-1]):
            self.finish_game()
            return
        self.snake.insert(0, head)
        if grows:
            self.score += 1
            self.food = self.random_food()
        else:
            self.snake.pop()

    def finish_game(self) -> None:
        previous = best_record(self.records).score
        self.state = "name"
        self.name_input = ""
        self.previous_best = previous
        self.stop_menu_music()
        pygame.key.stop_text_input()
        pygame.key.start_text_input()

    def draw_name(self) -> None:
        self.draw_header("Partida encerrada")
        self.draw_text(f"Pontuação: {self.score}", (self.screen.get_width() // 2, 170), self.font, GOLD)
        self.draw_text("Digite o nome do jogador:", (self.screen.get_width() // 2, 225), self.font)
        pygame.draw.rect(self.screen, PANEL, (self.screen.get_width() // 2 - 180, 255, 360, 42), border_radius=5)
        self.draw_text(self.name_input + "_", (self.screen.get_width() // 2, 276), self.font)
        self.draw_text("ENTER confirmar     ESC cancelar", (self.screen.get_width() // 2, self.screen.get_height() - 45), self.small_font, MUTED)

    def save_name(self) -> None:
        name = self.name_input.strip() or "Jogador"
        record = Record(name[:30], self.score, datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.records.insert(0, record)
        save_records(self.records)
        if self.score > self.previous_best:
            self.notice = f"Parabéns, {record.name}! Novo recorde: {self.score} pontos."
            self.state = "notice"
        else:
            self.show_menu()

    def handle_key(self, event: pygame.event.Event) -> None:
        key = event.key
        if self.state == "menu":
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % 4
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % 4
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                (self.new_game, lambda: self.set_state("records"), lambda: self.set_state("options"), self.close)[self.menu_index]()
            elif key == pygame.K_ESCAPE:
                self.close()
        elif self.state in ("records", "options"):
            if self.state == "options" and key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % 3
            elif self.state == "options" and key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % 3
            elif key in (pygame.K_ESCAPE, pygame.K_RETURN) and self.state == "records":
                self.show_menu()
            elif key == pygame.K_ESCAPE:
                self.show_menu()
            elif self.state == "options" and key == pygame.K_RETURN:
                self.change_option()
        elif self.state == "game":
            if not self.game_started:
                self.game_started = True
            elif key == pygame.K_q:
                self.show_menu()
            else:
                directions = {pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0)}
                if key in directions and directions[key] != (-self.direction[0], -self.direction[1]):
                    self.next_direction = directions[key]
        elif self.state == "name":
            if key == pygame.K_RETURN:
                self.save_name()
            elif key == pygame.K_ESCAPE:
                self.show_menu()
            elif key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.name_input) < 30:
                self.name_input += event.unicode
        elif self.state == "notice" and key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
            self.show_menu()

    def change_option(self) -> None:
        if self.menu_index == 0:
            sizes = {(20, 10): (30, 15), (30, 15): (40, 20), (40, 20): (20, 10)}
            self.settings.width, self.settings.height = sizes[(self.settings.width, self.settings.height)]
        elif self.menu_index == 1:
            self.settings.fullscreen = not self.settings.fullscreen
        save_settings(self.settings)
        flags = pygame.FULLSCREEN if self.settings.fullscreen else 0
        self.screen = pygame.display.set_mode(self.window_size(), flags)

    def set_state(self, state: str) -> None:
        self.state = state
        self.menu_index = 0

    def show_menu(self) -> None:
        self.state = "menu"
        self.menu_index = 0
        self.start_menu_music()

    def close(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
            if self.state == "game" and self.game_started and pygame.time.get_ticks() - self.last_tick >= TICK_MS:
                self.move()
                self.last_tick = pygame.time.get_ticks()
            if self.state == "menu":
                self.draw_menu()
            elif self.state == "records":
                self.draw_records()
            elif self.state == "options":
                self.draw_options()
            elif self.state == "game":
                self.draw_game()
            elif self.state == "name":
                self.draw_name()
            else:
                self.draw_header("Novo recorde!")
                self.draw_text(self.notice, (self.screen.get_width() // 2, 230), self.font, GOLD)
                self.draw_text("ENTER continuar", (self.screen.get_width() // 2, self.screen.get_height() - 45), self.small_font, MUTED)
            pygame.display.flip()
            self.clock.tick(60)
        self.stop_menu_music()
        pygame.quit()


if __name__ == "__main__":
    SnakeGame().run()
