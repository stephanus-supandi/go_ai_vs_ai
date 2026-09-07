"""Pygame rendering ONLY.

This module reads a GameState and a ViewInfo struct and draws pixels.
It contains zero game rules and never mutates game state.

Layout model (structural, not ad-hoc pixel nudging):
  * window height = max(board_px, MIN_WINDOW_HEIGHT), so the info panel
    always has enough vertical room even for 5x5 boards
  * the board square is vertically centred in the left region
  * the panel is divided into reserved vertical sections
    (title / players / meta / status / log / controls); every section
    advances the cursor by a FIXED height independent of its content,
    so sections can never overlap each other
  * every text line is clipped to the panel width using font metrics,
    so nothing can overflow horizontally
  * the log has a fixed reserved height (LOG_LINES rows); the controls
    are pinned to the window bottom with a guaranteed gap
  * star points: only valid configurations (9/13/19). 5x5 draws none.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import pygame

from game.board import BLACK, EMPTY, WHITE

BOARD_COLOR = (222, 184, 110)
LINE_COLOR = (40, 35, 25)
PANEL_BG = (28, 30, 34)
PANEL_FG = (235, 235, 235)
ACCENT = (255, 90, 90)
DIM = (150, 150, 150)
PAUSE_COLOR = (255, 210, 90)
THINK_COLOR = (120, 220, 140)
SEPARATOR = (60, 60, 64)

STAR_POINTS = {
    19: [(3, 3), (3, 9), (3, 15), (9, 3), (9, 9), (9, 15),
         (15, 3), (15, 9), (15, 15)],
    13: [(3, 3), (3, 6), (3, 9), (6, 3), (6, 6), (6, 9),
         (9, 3), (9, 6), (9, 9)],
    9: [(2, 2), (2, 6), (6, 2), (6, 6), (4, 4)],
    # 5x5: intentionally absent - no standard star points exist.
}

# ---------------- panel layout constants (pixels) ---------------- #
PANEL_WIDTH = 320
PAD_X = 18
PAD_TOP = 16
PAD_BOTTOM = 20
LINE_H = 24           # normal text line height (font 22)
LINE_H_SMALL = 20     # log / controls line height (font 18)
TITLE_H = 34          # title line height (font 30)
SECTION_GAP = 14
STATUS_SLOT_BIG = 30  # status headline (font 30)
STATUS_H = STATUS_SLOT_BIG + 3 * LINE_H   # big + sub1 + sub2 + thinking
LOG_LABEL_H = 22
LOG_LINES = 6
LOG_H = LOG_LABEL_H + LOG_LINES * LINE_H_SMALL
CONTROLS_H = 3 * LINE_H_SMALL

MIN_WINDOW_HEIGHT = (PAD_TOP + TITLE_H + SECTION_GAP
                     + 4 * LINE_H + SECTION_GAP     # players section
                     + 3 * LINE_H + SECTION_GAP     # meta section
                     + STATUS_H + SECTION_GAP       # status section
                     + LOG_H + SECTION_GAP          # log section
                     + CONTROLS_H + PAD_BOTTOM)     # controls section


@dataclass
class ViewInfo:
    """Everything the UI needs beyond the game state itself."""
    black_name: str = "Black AI"
    white_name: str = "White AI"
    thinking: bool = False          # current AI is computing
    paused: bool = False
    last_think_seconds: float = 0.0
    console_log: list = field(default_factory=list)
    error_text: str = ""            # set only on a fatal engine/AI error


class GoWindow:
    def __init__(self, board_size: int = 19, margin: int = 40,
                 panel_width: int = PANEL_WIDTH, cell: int = None):
        pygame.init()
        self.n = board_size
        self.cell = cell or max(22, min(38, 760 // max(1, board_size - 1)))
        self.margin = margin
        self.panel_width = panel_width
        self.board_px = self.cell * (board_size - 1) + 2 * margin
        self.height = max(self.board_px, MIN_WINDOW_HEIGHT)
        self.offset_y = (self.height - self.board_px) // 2
        width = self.board_px + panel_width
        self.screen = pygame.display.set_mode((width, self.height))
        pygame.display.set_caption("Go - AI vs AI (prototype)")
        self.font = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)
        self.font_big = pygame.font.Font(None, 30)
        self.clock = pygame.time.Clock()

    # ------------------------------------------------------------------ #
    def _xy(self, point):
        r, c = point
        return (self.margin + c * self.cell,
                self.offset_y + self.margin + r * self.cell)

    # ------------------------------------------------------------------ #
    def draw(self, state, info: ViewInfo):
        s = self.screen
        s.fill(PANEL_BG)
        self._draw_board_area(state)
        pygame.draw.line(s, SEPARATOR, (self.board_px, 0),
                         (self.board_px, self.height), 1)
        self._draw_panel(state, info)
        pygame.display.flip()

    def tick(self, fps: int = 30):
        self.clock.tick(fps)

    # ------------------------------------------------------------------ #
    def _clip(self, txt, font, max_w):
        """Truncate txt so it never exceeds max_w pixels."""
        if font.size(txt)[0] <= max_w:
            return txt
        while txt and font.size(txt + "...")[0] > max_w:
            txt = txt[:-1]
        return txt + "..."

    def _text(self, surf, txt, x, y, font=None, color=PANEL_FG):
        f = font or self.font
        txt = self._clip(txt, f, self.panel_width - 2 * PAD_X)
        surf.blit(f.render(txt, True, color), (x, y))

    # ------------------------------------------------------------------ #
    def _draw_board_area(self, state):
        s = self.screen
        pygame.draw.rect(s, BOARD_COLOR,
                         (0, self.offset_y, self.board_px, self.board_px))
        n, cell, m = self.n, self.cell, self.margin
        top = self.offset_y
        # grid: lines run exactly through the intersection coordinates
        for i in range(n):
            p = m + i * cell
            pygame.draw.line(s, LINE_COLOR, (m, top + p),
                             (m + (n - 1) * cell, top + p), 1)
            pygame.draw.line(s, LINE_COLOR, (p, top + m),
                             (p, top + m + (n - 1) * cell), 1)
        # star points (only valid configurations; 5x5 has none)
        for sp in STAR_POINTS.get(n, []):
            if sp[0] < n and sp[1] < n:
                pygame.draw.circle(s, LINE_COLOR, self._xy(sp),
                                   max(3, cell // 9))
        # stones centred on intersections
        radius = int(cell * 0.47)
        for r in range(n):
            for c in range(n):
                v = state.board.grid[r][c]
                if v == EMPTY:
                    continue
                x, y = self._xy((r, c))
                if v == BLACK:
                    pygame.draw.circle(s, (15, 15, 15), (x, y), radius)
                    pygame.draw.circle(s, (80, 80, 80),
                                       (x - radius // 3, y - radius // 3),
                                       max(2, radius // 4))
                else:
                    pygame.draw.circle(s, (246, 246, 246), (x, y), radius)
                    pygame.draw.circle(s, (120, 120, 120), (x, y), radius, 1)
        # ko marker centred on the forbidden intersection
        if state.ko_point is not None:
            x, y = self._xy(state.ko_point)
            pygame.draw.rect(s, ACCENT, (x - 4, y - 4, 8, 8), 2)
        # last-move marker centred on the last stone
        last = state.last_move
        if last is not None and last.point is not None:
            x, y = self._xy(last.point)
            stone = state.board.get(last.point)
            mark = (240, 240, 240) if stone == BLACK else (20, 20, 20)
            pygame.draw.circle(s, mark, (x, y), max(3, radius // 3), 2)

    # ------------------------------------------------------------------ #
    def _draw_panel(self, state, info: ViewInfo):
        s = self.screen
        x0 = self.board_px + PAD_X
        y = PAD_TOP
        turn_name = "Black" if state.to_play == BLACK else "White"
        ai_name = info.black_name if state.to_play == BLACK else info.white_name

        # ---- TITLE section (reserved TITLE_H) ----
        self._text(s, "GO  -  AI vs AI", x0, y, self.font_big)
        y += TITLE_H + SECTION_GAP

        # ---- PLAYERS section (reserved 4 * LINE_H) ----
        self._text(s, f"Black: {info.black_name}", x0, y); y += LINE_H
        self._text(s, f"  captures: {state.captures[BLACK]}", x0, y,
                   color=DIM); y += LINE_H
        self._text(s, f"White: {info.white_name}", x0, y); y += LINE_H
        self._text(s, f"  captures: {state.captures[WHITE]}", x0, y,
                   color=DIM); y += LINE_H
        y += SECTION_GAP

        # ---- META section (reserved 3 * LINE_H) ----
        self._text(s, f"Move number : {state.move_number}", x0, y); y += LINE_H
        self._text(s, f"Turn        : {turn_name}", x0, y); y += LINE_H
        self._text(s, f"Last think  : {info.last_think_seconds:.2f}s", x0, y)
        y += LINE_H
        y += SECTION_GAP

        # ---- STATUS section (reserved STATUS_H, exactly one state) ----
        if info.error_text:
            self._text(s, "ERROR", x0, y, self.font_big, ACCENT)
            y += STATUS_SLOT_BIG
            self._text(s, info.error_text, x0, y, color=ACCENT); y += LINE_H
            self._text(s, "traceback on console", x0, y, color=DIM)
            y += LINE_H
            y += LINE_H                      # thinking slot stays empty
        elif state.game_over:
            winner = state.winner()
            wname = {BLACK: "BLACK wins", WHITE: "WHITE wins",
                     None: "Draw"}[winner]
            self._text(s, "GAME OVER", x0, y, self.font_big, ACCENT)
            y += STATUS_SLOT_BIG
            self._text(s, f"{wname}  ({state.result_string()})", x0, y)
            y += LINE_H
            sub = "(by resignation)" if state.resigned_by is not None else ""
            self._text(s, sub, x0, y, color=DIM); y += LINE_H
            y += LINE_H                      # thinking slot stays empty
        elif info.paused:
            self._text(s, "PAUSED", x0, y, self.font_big, PAUSE_COLOR)
            y += STATUS_SLOT_BIG
            y += LINE_H
            y += LINE_H
            y += LINE_H
        else:
            self._text(s, "Playing", x0, y, self.font_big)
            y += STATUS_SLOT_BIG
            y += LINE_H
            y += LINE_H
            if info.thinking:
                dots = "." * (int(time.time() * 3) % 4)
                self._text(s, f"{ai_name} ({turn_name}) thinking{dots}",
                           x0, y, color=THINK_COLOR)
            y += LINE_H
        y += SECTION_GAP

        # ---- LOG section (reserved LOG_H, fixed row count) ----
        self._text(s, "Log:", x0, y, color=DIM); y += LOG_LABEL_H
        recent = info.console_log[-LOG_LINES:]
        for i in range(LOG_LINES):
            if i < len(recent):
                self._text(s, recent[i], x0, y,
                           font=self.font_small, color=DIM)
            y += LINE_H_SMALL
        y += SECTION_GAP

        # ---- CONTROLS section (pinned to window bottom) ----
        yb = self.height - PAD_BOTTOM - CONTROLS_H
        self._text(s, "SPACE  pause/resume", x0, yb,
                   font=self.font_small, color=DIM)
        self._text(s, "R      restart", x0, yb + LINE_H_SMALL,
                   font=self.font_small, color=DIM)
        self._text(s, "ESC    quit", x0, yb + 2 * LINE_H_SMALL,
                   font=self.font_small, color=DIM)
