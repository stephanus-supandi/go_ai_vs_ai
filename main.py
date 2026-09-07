"""Entry point: AI-vs-AI Go with a Pygame viewer or headless batch mode.

Both modes share exactly one engine and AI layer:
    game.board / game.rules / game.scoring / game.game_state
    ai.random_ai / ai.mcts
The UI (ui.pygame_board) is render-only and never contains rules.

Fail-fast policy: exceptions raised by an AI or by GameState
(IllegalMoveError, GameOverError) propagate.  Nothing is ever converted
into a pass, in headless mode or in the GUI.

Examples:
  python main.py --size 9 --black mcts --white random --iters 200
  python main.py --headless --games 5 --size 9 --black mcts --white random
  python main.py            # 19x19 MCTS vs MCTS (SLOW in pure Python)
"""
from __future__ import annotations

import argparse
import time
import traceback

from ai.mcts import MCTSAI
from ai.random_ai import RandomAI
from game.board import BLACK, WHITE
from game.game_state import GameState

COLOR_NAME = {BLACK: "Black", WHITE: "White"}


def make_ai(kind: str, color: int, args, seed):
    if kind == "random":
        return RandomAI(color, seed=seed)
    if kind == "mcts":
        return MCTSAI(color, iterations=args.iters,
                      exploration=args.explore, seed=seed)
    raise ValueError(f"unknown ai kind: {kind!r} (use 'random' or 'mcts')")


def new_game_and_ais(args, seed_base=None):
    state = GameState(size=args.size, komi=args.komi)
    base = seed_base if seed_base is not None else (args.seed or 0)
    ais = {
        BLACK: make_ai(args.black, BLACK, args,
                       None if args.seed is None else base + 1),
        WHITE: make_ai(args.white, WHITE, args,
                       None if args.seed is None else base + 2),
    }
    return state, ais


def apply_move(state, ais, log_lines=None):
    """Ask the current AI for a move and apply it. Returns (line, think).

    Fail-fast: any exception raised by the AI or by GameState.play()
    propagates to the caller.  A buggy AI must stop the run with a
    visible traceback; it is never coerced into a pass.
    """
    color = state.to_play
    ai = ais[color]
    t0 = time.perf_counter()
    move = ai.choose_move(state)
    think = time.perf_counter() - t0

    if move is None:
        state.pass_turn()
        desc = "pass"
    else:
        captured = state.play(move)
        desc = f"{move} cap={len(captured)}"

    line = (f"#{state.move_number:>3} {COLOR_NAME[color][0]} {desc:<14} "
            f"({think:.2f}s)")
    print(line)
    if log_lines is not None:
        log_lines.append(line)
        del log_lines[:-8]
    return line, think


def stats_row(game_no, state, runtime):
    b, w = state.score()
    winner = state.winner()
    wname = {BLACK: "Black", WHITE: "White", None: "Draw"}[winner]
    return {
        "game": game_no,
        "winner": wname,
        "moves": state.move_number,
        "black_captures": state.captures[BLACK],
        "white_captures": state.captures[WHITE],
        "score": f"B {b} - W {w:.1f}",
        "result": state.result_string(),
        "runtime": runtime,
    }


# ---------------------------------------------------------------------- #
# Headless batch mode
# ---------------------------------------------------------------------- #
def run_headless(args):
    rows = []
    for g in range(1, args.games + 1):
        seed_base = None if args.seed is None else args.seed + 1000 * (g - 1)
        state, ais = new_game_and_ais(args, seed_base)
        print(f"\n=== Game {g}: {args.black}(B) vs {args.white}(W), "
              f"size={args.size}, iters={args.iters} ===")
        t0 = time.perf_counter()
        max_moves = args.size * args.size * 3   # safety guard ONLY
        while not state.game_over and state.move_number < max_moves:
            apply_move(state, ais)
        if state.game_over:
            termination = "passes"      # natural double-pass termination
        else:
            termination = "cap"         # safety cap reached (abnormal)
            # Finish safely; never call pass_turn() on a terminal state.
            if not state.game_over:
                state.pass_turn()
            if not state.game_over:
                state.pass_turn()
        runtime = time.perf_counter() - t0
        row = stats_row(g, state, runtime)
        row["termination"] = termination
        rows.append(row)
        if termination == "cap":
            print(f"[warn] game {g} ended by the safety move cap, NOT by "
                  f"a natural double pass")

    hdr = (f"{'Game':>4} | {'Winner':<6} | {'Moves':>5} | {'BCap':>4} | "
           f"{'WCap':>4} | {'Result':<7} | {'End':<6} | {'Score':<14} | "
           f"{'Runtime':>8}")
    print("\n" + hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['game']:>4} | {r['winner']:<6} | {r['moves']:>5} | "
              f"{r['black_captures']:>4} | {r['white_captures']:>4} | "
              f"{r['result']:<7} | {r['termination']:<6} | "
              f"{r['score']:<14} | {r['runtime']:>7.1f}s")

    bw = sum(1 for r in rows if r["winner"] == "Black")
    ww = sum(1 for r in rows if r["winner"] == "White")
    avg_moves = sum(r["moves"] for r in rows) / max(1, len(rows))
    avg_rt = sum(r["runtime"] for r in rows) / max(1, len(rows))
    print(f"\nSummary: Black {bw} - White {ww} | avg moves {avg_moves:.1f} "
          f"| avg runtime {avg_rt:.1f}s")


# ---------------------------------------------------------------------- #
# GUI mode (AI vs AI, human only watches)
# ---------------------------------------------------------------------- #
def run_gui(args):
    import pygame
    from ui.pygame_board import GoWindow, ViewInfo

    window = GoWindow(board_size=args.size)
    state, ais = new_game_and_ais(args)
    log_lines = []
    paused = False
    last_move_at = 0.0
    last_think = 0.0
    running = True
    crashed = None

    info = ViewInfo(black_name=ais[BLACK].name, white_name=ais[WHITE].name,
                    console_log=log_lines)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    state, ais = new_game_and_ais(args)
                    log_lines.clear()
                    paused = False
                    last_move_at = time.perf_counter()
                    last_think = 0.0
                    info.black_name = ais[BLACK].name
                    info.white_name = ais[WHITE].name
                    info.last_think_seconds = 0.0
                    info.error_text = ""

        now = time.perf_counter()
        if (not paused and not state.game_over and crashed is None
                and now - last_move_at >= args.delay):
            info.thinking = True
            info.paused = paused
            window.draw(state, info)
            pygame.event.pump()
            try:
                _, think = apply_move(state, ais, log_lines)
            except Exception as exc:
                # Report the bug, show it in the UI, stop safely, and
                # re-raise after pygame shutdown.  Never a silent pass.
                traceback.print_exc()
                info.thinking = False
                info.error_text = f"{type(exc).__name__}: {exc}"
                log_lines.append(f"[error] {info.error_text}")
                window.draw(state, info)
                pygame.event.pump()
                pygame.time.wait(1500)
                crashed = exc
                running = False
            else:
                last_think = think
                last_move_at = time.perf_counter()
                if state.game_over:
                    r = stats_row("-", state, 0.0)
                    print(f"\nGAME OVER: {r['winner']} wins ({r['result']}), "
                          f"moves={r['moves']}, score={r['score']}")

        info.thinking = False
        info.paused = paused
        info.last_think_seconds = last_think
        window.draw(state, info)
        window.tick(30)

    pygame.quit()
    if crashed is not None:
        raise crashed


# ---------------------------------------------------------------------- #
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Go AI vs AI prototype")
    ap.add_argument("--size", type=int, default=19, choices=[5, 9, 13, 19])
    ap.add_argument("--black", default="mcts", choices=["mcts", "random"])
    ap.add_argument("--white", default="mcts", choices=["mcts", "random"])
    ap.add_argument("--iters", type=int, default=200,
                    help="MCTS iterations per move")
    ap.add_argument("--explore", type=float, default=1.4142)
    ap.add_argument("--komi", type=float, default=7.5)
    ap.add_argument("--delay", type=float, default=0.2,
                    help="GUI: seconds between moves (watchability)")
    ap.add_argument("--seed", type=int, default=None,
                    help="master seed for deterministic AI play")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--games", type=int, default=1)
    return ap.parse_args(argv)


def main():
    args = parse_args()
    if args.headless:
        run_headless(args)
    else:
        run_gui(args)


if __name__ == "__main__":
    main()
