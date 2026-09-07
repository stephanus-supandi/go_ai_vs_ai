# Go AI vs AI

A from-scratch Go engine and AI-vs-AI playground written in Python.

No KataGo.

No external Go engine.

No giant framework.

Just a small game engine, a Random AI, an MCTS AI, a test suite, and two computers trying to beat each other at Go.

> **Make it correct → make it understandable → make it faster → make it smarter.**

---

## Why?

Go is a deceptively simple game.

The rules are small.

The search space is not.

So instead of jumping directly into neural networks, GPUs, policy networks, value networks, or some giant AI framework, this project starts at the bottom:

**build the damn game engine first.**

Because building an AI on top of broken rules is a great way to produce very confident garbage.

The goal of this project is not to build the next AlphaGo.

The goal is to understand how the pieces actually work.

---

## Project Philosophy

This project follows a simple engineering-first approach:
1. Implement the rules.
2. Test the rules.
3. Separate game state from AI.
4. Implement a stupid baseline.
5. Implement MCTS.
6. Test the search.
7. Run AI-vs-AI experiments.
8. Only then think about making it smarter.

In other words:

> **One bug at a time.**

---

## Architecture

go_ai_vs_ai/
│
├── main.py
├── requirements.txt
├── __init__.py
│
├── game/
│   ├── board.py
│   ├── rules.py
│   ├── game_state.py
│   ├── scoring.py
│   └── __init__.py
│
├── ai/
│   ├── random_ai.py
│   ├── mcts.py
│   └── __init__.py
│
├── ui/
│   ├── pygame_board.py
│   └── __init__.py
│
└── tests/
    ├── test_liberty.py
    ├── test_capture.py
    ├── test_ko.py
    ├── test_rules.py
    ├── test_mcts.py
    └── __init__.py

The important separation is:
             ┌─────────────┐
             │     UI      │
             └──────┬──────┘
                    │
             ┌──────▼──────┐
             │     AI      │
             │ Random/MCTS │
             └──────┬──────┘
                    │
             ┌──────▼──────┐
             │  GameState  │
             └──────┬──────┘
                    │
          ┌─────────┴─────────┐
          │                   │
     ┌────▼────┐        ┌─────▼─────┐
     │  Rules  │        │  Scoring  │
     └────┬────┘        └───────────┘
          │
     ┌────▼────┐
     │  Board  │
     └─────────┘

The game engine does not know or care which AI is playing.

The AI ​​does not modify the UI.

The UI does not contain the game rules.

Keep the pieces boring.

Boring is good.

---

## Game Engine

Board
game/board.py

The Boardclass handles low-level board operations:

- board representation
- coordinates
- neighboring points
- empty points
- group detection
- liberties
- stone placement
- captures
- board cloning

Coordinates use:
(row, col)

Colors are represented as:
EMPTY = 0
BLACK = 1
WHITE = 2
Groups and liberties are calculated using flood-fill style traversal.

---

## Rules
game/rules.py

The rules layer handles move legality.

- Currently implemented:
- board bounds
- occupied-point detection
- suicide prevention
- captures
- simple ko
- pass
- resignation
- game termination

Illegal moves raise:
IllegalMoveError

The engine does not silently convert an illegal move into a pass.
If something is wrong, it should fail loudly.
That's useful when debugging an AI.

---

## Game State
game/game_state.py
GameStaterepresents the current game.

It contains information such as:
- current board
- side to play
- ko point
- pass counter
- move history
- captured stones
- resignation state
- game-over state

The game state is mutable during normal play.

For search algorithms, the state can be cloned:
state.clone()

This is important for MCTS because simulations must not corrupt the real game.
The real game stays outside the search tree.

---

## Scoring

game/scoring.py
The current implementation uses a simplified area-scoring approach:

score =
    stones on board
    +
    surrounded empty territory

Empty regions are assigned only when they are bordered exclusively by one color.

Neutral regions remain neutral.

Komi is applied to White.

This is intentionally a simplified scoring model.

It is not intended to reproduce every detail of tournament Go scoring.

In particular, this project currently does not attempt full adjudication of:
- dead stones
- seki
- advanced superko variants
- complete tournament rule sets

The objective is to have a small, understandable rules engine that can support experimentation.

---

## AI
RandomAI
ai/random_ai.py

The baseline AI is deliberately stupid.

It chooses uniformly from legal moves.

That's it.

No evaluation function.

No opening book.

No neural network.

No cleverness.

The point of RandomAI is to provide a simple baseline and an opponent for testing MCTS.

It also gives us something extremely useful:
	a machine that can play Go badly, consistently, and automatically.

---

## Monte Carlo Tree Search
ai/mcts.py

The second player is a basic Monte Carlo Tree Search implementation.

The implementation follows the standard four conceptual phases:
Selection
    ↓
Expansion
    ↓
Simulation
    ↓
Backpropagation

---

## Selection

Starting from the root, MCTS follows the tree using UCT:
UCT =
    exploitation
    +
    exploration

The exploration parameter controls the balance between:
- moves that already look good
- moves that haven't been explored enough

---

## Expansion
When a leaf node still has unexplored legal moves, MCTS expands one of them.

The child state represents the game after that move.

---

## Simulation
The new state is played forward using a lightweight stochastic rollout policy.

The current rollout includes:
- random legal move selection
- avoidance of obvious own-eye moves
- a small pass bias
- a rollout safety limit

This is intentionally lightweight.

It is not a strong Go evaluation policy.

It's a baseline search engine.

---

## Backpropagation
Simulation results are propagated back through the tree.

Each node tracks wins from the perspective of:
	player_just_moved

This avoids the classic MCTS perspective bug where the meaning of "win" accidentally flips between players.

The child node's statistics can therefore be interpreted directly from the perspective of the player choosing that child.

Small details.

Huge debugging potential.

---

## State Immutability During Search
MCTS must be allowed to explore hypothetical games without destroying the actual game.

Conceptually:
REAL GAME STATE
       │
       ├── clone → simulation A
       │
       ├── clone → simulation B
       │
       └── clone → simulation C

The supplied GameStateis never mutated by MCTSAI.choose_move().

This keeps the search isolated from the real game.

---

## Testing
Tests are not decoration.

They are part of the engine.

The current test suite covers:
- liberties
- group detection
- captures
- suicide
- ko
- rule validation
- game state behavior
- MCTS behavior
- AI-vs-AI game execution

Run the complete suite with:
python -m unittest discover -s tests -t . -v

Current verified result:
Ran 47 tests
OK
47/47 PASS.

---

## Running the Project
Requirements
Python 3.14 was used during development.

Install dependencies:
python -m pip install -r requirements.txt

The GUI uses:
pygame-ce

---

## Headless Mode
Run an AI-vs-AI game without the graphical interface:
python main.py --headless

For example:
python main.py --headless --size 5 --black mcts --white random

Available AI players:
- random
- mcts

Example MCTS-vs-MCTS:
python main.py --headless --size 5 --black mcts --white mcts

---

## GUI
Launch the graphical version:
python main.py

Example:
python main.py --size 5 --black mcts --white random

The GUI provides:
- board rendering
- player information
- game status
- move log
- pause/resume
- restart
- configurable AI matchup
- configurable board size

---

## Board Sizes
The engine can represent different board sizes.

The current experimental focus is on:
5 × 5
9 × 9

The board representation also supports larger sizes, including 13×13 and 19×19, but practical AI experimentation and validation are currently focused on smaller boards.

Why?
Because debugging a tiny game is much easier than debugging a giant search tree.

---

## Random-vs-Random and the Infinite Go Problem
There is an interesting engineering problem here.

Pure random play can produce cycles.

The current rules implement simple ko , not full positional superko.

Therefore, Random-vs-Random is not guaranteed to terminate naturally in every possible game.

Instead of pretending this cannot happen, the executable uses a safety move cap for potentially cycling random games.

That gives us:
natural game termination
        OR
safety termination

This is a test-engineering decision, not a claim that random Go is guaranteed to finish under the simplified rules.

---

## Current Status

The current project has:
- Board representation
- Group detection
- Liberty calculation
- Capture mechanics
- Suicide prevention
- It's simple
- Pass handling
- Resignation
- Game termination
- Simplified area scoring
- RandomAI
- MCTS
- Pygame GUI
- Unit tests
- AI-vs-AI execution
- Headless mode
- 5×5 experimentation
- 9×9 experimentation
Verified regression suite:
47 / 47 tests passing

---

## What This Is NOT

This is not:
- KataGo
- AlphaGo
- a neural Go engine
- a tournament-strength Go engine
- a GPU-accelerated search system
- a complete implementation of every Go ruleset

Don't expect this thing to casually defeat a serious 19×19 Go engine.

It won't.

That's not the point.

---

## What Comes Next?

Possible future directions:

Engine
- stronger ko/superko handling
- more complete rulesets
- better scoring
- performance profiling
- faster board operations

MCTS
- stronger rollout policies
- better move ordering
- transposition handling
- tree reuse
- improved evaluation
- parallel simulations

AI
Eventually:
    RandomAI
       ↓
     MCTS
       ↓
 better evaluation
       ↓
  neural network

But only when the lower layers are understood well enough to deserve one.

---

## Engineering Principle
A recurring principle in this project is:
	Don't make the AI smarter before making the system correct.

A beautiful AI that violates the rules is still just a fancy bug generator.

So the development order is intentionally boring:

correctness
    ↓
understanding
    ↓
testing
    ↓
performance
    ↓
intelligence

---

## BLOON-ish Thinking
This project is also an experiment in building computational systems from the bottom up.

Instead of hiding everything behind a large framework:
small primitive
      ↓
explicit state
      ↓
explicit rules
      ↓
explicit computation
      ↓
observable behavior

The code should be understandable enough that when something goes wrong, we can actually find the damn thing.

No magic required.

Just computation.

---

## The AlphaGo Story

Before trying to build something "smart", it is worth understanding how one of
the most influential game-playing AI systems was actually built.

- [AlphaGo — Google DeepMind](https://deepmind.google/research/alphago/)
  — The story, matches, ideas, and technical legacy.

- [AlphaGo: Mastering the Ancient Game of Go](https://research.google/blog/alphago-mastering-the-ancient-game-of-go-with-machine-learning/)
  — An accessible introduction from the original DeepMind team.

- [Mastering the Game of Go with Deep Neural Networks and Tree Search](https://doi.org/10.1038/nature16961)
  — The original AlphaGo research paper.

- [AlphaGo Zero: Starting from Scratch](https://deepmind.google/blog/alphago-zero-starting-from-scratch/)
  — What happened when the human knowledge was removed and the system
    learned through self-play.

- [AlphaZero: Shedding New Light on Chess, Shogi, and Go](https://deepmind.google/blog/alphazero-shedding-new-light-on-chess-shogi-and-go/)
  — The approach generalized beyond Go.

> Our project is nowhere near AlphaGo.
>
> That's fine.
>
> First we need to make sure a stone has the damn liberty it is supposed to have.

---

## License

### License to Let Go of Software Bugs™

This project is released under the BLOON UNIVERSITY™ License.

See [LICENSE](LICENSE) for the actual legal terms.

If you find a bug...

let it go.

...into an issue tracker.