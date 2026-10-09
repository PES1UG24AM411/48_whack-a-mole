
import math
import random
import pygame

from .hole import Hole


DARK_BROWN = (60, 40, 20)
MOLE_BROWN = (140, 95, 55)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRASS_GREEN = (120, 170, 90)
PANEL = (70, 100, 55)
YELLOW = (255, 220, 90)

DIFFICULTIES = {
    "Easy": {"spawn": 0.012, "duration": 65},
    "Medium": {"spawn": 0.020, "duration": 45},
    "Hard": {"spawn": 0.035, "duration": 30},
}


class GameEngine:
    def __init__(self, width, height, rows=3, cols=3):
        self.width = width
        self.height = height
        self.holes = []

        spacing_x = width // (cols + 1)
        spacing_y = (height - 100) // (rows + 1)

        for r in range(rows):
            for c in range(cols):
                cx = spacing_x * (c + 1)
                cy = 80 + spacing_y * (r + 1)
                self.holes.append(Hole(cx, cy, hit_size=66))

        self.round_seconds = 30
        self.score = 0
        self.misses = 0
        self.time_left_frames = self.round_seconds * 60

        self.state = "playing"
        self.game_over = False

        self.difficulty = "Medium"
        self.spawn_chance = DIFFICULTIES[self.difficulty]["spawn"]
        self.mole_up_frames = DIFFICULTIES[self.difficulty]["duration"]

        self.font = pygame.font.SysFont("Arial", 28)
        self.small_font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 42, bold=True)

        self.sound_enabled = False
        self.hit_sound = None
        self.miss_sound = None
        self.end_sound = None
        self._init_sounds()

    # Task 4: Create sounds without requiring external audio files.
    def _init_sounds(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=22050,
                    size=-16,
                    channels=1,
                    buffer=512,
                )

            rate = 22050

            def create_tone(freq, duration, volume=0.3, falling=False):
                count = int(rate * duration)
                samples = bytearray()

                for i in range(count):
                    progress = i / max(1, count)

                    current_freq = (
                        freq * (1 - 0.5 * progress)
                        if falling
                        else freq
                    )

                    envelope = min(
                        1.0,
                        i / 150,
                        (count - i) / 400,
                    )

                    sample = int(
                        32767
                        * volume
                        * max(0, envelope)
                        * math.sin(
                            2 * math.pi * current_freq * i / rate
                        )
                    )

                    samples.extend(
                        sample.to_bytes(2, "little", signed=True)
                    )

                return pygame.mixer.Sound(buffer=bytes(samples))

            self.hit_sound = create_tone(880, 0.10)
            self.miss_sound = create_tone(220, 0.12, 0.25)
            self.end_sound = create_tone(
                520, 0.45, 0.35, falling=True
            )

            self.sound_enabled = True

        except (pygame.error, OSError, ValueError):
            # The game should still work if audio is unavailable.
            self.sound_enabled = False

    def _play(self, sound):
        if self.sound_enabled and sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    # Task 1: Handle clicks without awarding points twice.
    def _handle_click(self, pos):
        candidates = [
            hole
            for hole in self.holes
            if hole.active and hole.rect().collidepoint(pos)
        ]

        if candidates:
            # If hitboxes overlap, select only the nearest active mole.
            target = min(
                candidates,
                key=lambda hole: (
                    (hole.center_x - pos[0]) ** 2
                    + (hole.center_y - pos[1]) ** 2
                ),
            )

            if target.whack():
                self.score += 1
                self._play(self.hit_sound)
                return

        # Clicking an empty hole or missing a mole does not score.
        self.misses += 1
        self._play(self.miss_sound)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return

        if self.state == "playing":
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                self._handle_click(event.pos)
            return

        # Task 3: Keyboard controls on the game-over screen.
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(
                    pygame.event.Event(pygame.QUIT)
                )
            elif event.key in (pygame.K_1, pygame.K_e):
                self.start_round("Easy")
            elif event.key in (
                pygame.K_2,
                pygame.K_m,
                pygame.K_RETURN,
                pygame.K_SPACE,
            ):
                self.start_round("Medium")
            elif event.key in (pygame.K_3, pygame.K_h):
                self.start_round("Hard")

        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            self._handle_menu_click(event.pos)

    def _menu_rects(self):
        button_width = 125
        gap = 12

        start_x = (
            self.width - (button_width * 3 + gap * 2)
        ) // 2

        y = self.height // 2 + 55

        buttons = {}

        for i, name in enumerate(("Easy", "Medium", "Hard")):
            buttons[name] = pygame.Rect(
                start_x + i * (button_width + gap),
                y,
                button_width,
                48,
            )

        buttons["Exit"] = pygame.Rect(
            self.width // 2 - 65,
            y + 62,
            130,
            42,
        )

        return buttons

    def _handle_menu_click(self, pos):
        for name, rect in self._menu_rects().items():
            if rect.collidepoint(pos):
                if name == "Exit":
                    pygame.event.post(
                        pygame.event.Event(pygame.QUIT)
                    )
                else:
                    self.start_round(name)
                return

    # Task 3: Reset the game and apply the selected difficulty.
    def start_round(self, difficulty="Medium"):
        self.difficulty = difficulty
        settings = DIFFICULTIES[difficulty]

        self.spawn_chance = settings["spawn"]
        self.mole_up_frames = settings["duration"]

        self.score = 0
        self.misses = 0
        self.time_left_frames = self.round_seconds * 60

        self.state = "playing"
        self.game_over = False

        for hole in self.holes:
            hole.active = False
            hole.timer = 0

    def handle_input(self):
        pass

    # Update the game timer and mole spawning.
    def update(self):
        if self.state != "playing":
            return

        self.time_left_frames -= 1

        # Task 2: Stop the round when the timer reaches zero.
        if self.time_left_frames <= 0:
            self.time_left_frames = 0
            self.game_over = True
            self.state = "game_over"
            self._play(self.end_sound)
            return

        for hole in self.holes:
            hole.update()

            if (
                not hole.active
                and random.random() < self.spawn_chance
            ):
                hole.pop_up(self.mole_up_frames)

    def _draw_center(self, screen, text, font, color, y):
        surface = font.render(text, True, color)

        screen.blit(
            surface,
            (
                self.width // 2 - surface.get_width() // 2,
                y,
            ),
        )

    def render(self, screen):
        if self.state == "playing":
            for hole in self.holes:
                pygame.draw.circle(
                    screen,
                    DARK_BROWN,
                    (hole.center_x, hole.center_y),
                    40,
                )

                if hole.active:
                    pygame.draw.circle(
                        screen,
                        MOLE_BROWN,
                        (hole.center_x, hole.center_y),
                        32,
                    )

                    # Simple eyes to make the mole visible.
                    pygame.draw.circle(
                        screen,
                        WHITE,
                        (hole.center_x - 9, hole.center_y - 5),
                        4,
                    )

                    pygame.draw.circle(
                        screen,
                        WHITE,
                        (hole.center_x + 9, hole.center_y - 5),
                        4,
                    )

            score_text = self.font.render(
                f"Score: {self.score}", True, BLACK
            )
            screen.blit(score_text, (10, 10))

            seconds = max(0, self.time_left_frames // 60)

            timer_text = self.font.render(
                f"Time: {seconds}s", True, BLACK
            )
            screen.blit(
                timer_text,
                (self.width - 140, 10),
            )

            return

        # Task 2: Display the final score and replay menu.
        overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA,
        )
        overlay.fill((20, 30, 15, 220))
        screen.blit(overlay, (0, 0))

        self._draw_center(
            screen,
            "GAME OVER",
            self.title_font,
            WHITE,
            115,
        )

        self._draw_center(
            screen,
            f"Final Score: {self.score}",
            self.font,
            YELLOW,
            180,
        )

        self._draw_center(
            screen,
            "Choose a difficulty to play again",
            self.small_font,
            WHITE,
            235,
        )

        # Task 3: Difficulty buttons and exit button.
        for name, rect in self._menu_rects().items():
            color = DARK_BROWN if name == "Exit" else PANEL

            pygame.draw.rect(
                screen,
                color,
                rect,
                border_radius=8,
            )

            pygame.draw.rect(
                screen,
                WHITE,
                rect,
                width=2,
                border_radius=8,
            )

            label = self.small_font.render(
                name, True, WHITE
            )

            screen.blit(
                label,
                (
                    rect.centerx - label.get_width() // 2,
                    rect.centery - label.get_height() // 2,
                ),
            )

        self._draw_center(
            screen,
            "Keys: 1 Easy   2 Medium   3 Hard   Q/Esc Exit",
            self.small_font,
            WHITE,
            self.height - 35,
        )

