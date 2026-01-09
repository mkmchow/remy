"""
Animated Eyes UI for Remy AI Desk Companion
Simple shape-based robot eyes with emotion-specific shapes
"""
import pygame
import pygame.gfxdraw  # For anti-aliased drawing
import math
import time
import random
from typing import Optional, List, Tuple
from collections import deque
import threading

from config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    BG_COLOR,
    EYE_COLOR,
    EYE_GLOW_COLOR,
    DEBUG_BG_COLOR,
    DEBUG_TEXT_COLOR,
    DEBUG_MODE,
    FPS,
    EyeState
)


# Pink color theme
PINK_PRIMARY = (255, 130, 170)      # Main eye color


class AnimatedEyes:
    """
    Simple shape-based robot eyes with emotion-specific shapes:
    - Neutral: Rounded rectangle
    - Happy: Rounded triangle (beveled top corners)
    - Sad: Oval/ellipse
    - Angry: Squinted rectangle
    - Surprised: Large circle
    """
    
    def __init__(self, center_x: int, center_y: int):
        self.center_x = center_x
        self.center_y = center_y
        
        # Eye dimensions (scaled for 480x320 screen)
        self.eye_width = 50
        self.eye_height = 90
        self.eye_gap = 140  # Space between eyes
        
        # Calculate eye centers
        self.left_eye_x = center_x - self.eye_gap // 2 - self.eye_width // 2
        self.right_eye_x = center_x + self.eye_gap // 2 + self.eye_width // 2
        self.eye_y = center_y
        
        # Separate states
        self.conversation_state = EyeState.IDLE
        self.emotion_state = EyeState.NEUTRAL
        self.state_time = 0.0
        self.emotion_time = 0.0
        
        # Animation
        self.animation_time = 0.0
        self.blink_progress = 0.0  # 0 = open, 1 = closed
        self.last_blink_time = 0.0
        self.next_blink_interval = random.uniform(2.0, 5.0)
        self.is_blinking = False
        self.blink_duration = 0.15
        
        # Current animated values (for smooth transitions)
        self.current_width = float(self.eye_width)
        self.current_height = float(self.eye_height)
        self.target_width = float(self.eye_width)
        self.target_height = float(self.eye_height)
        
        # Audio level
        self.audio_level = 0.0
    
    def set_state(self, state: str):
        """Change conversation state"""
        if state != self.conversation_state:
            self.conversation_state = state
            self.state_time = 0.0
    
    def set_emotion(self, emotion: str):
        """Change emotion state"""
        if emotion != self.emotion_state:
            self.emotion_state = emotion
            self.emotion_time = 0.0
    
    def set_audio_level(self, level: float):
        """Set audio level for animations"""
        self.audio_level = max(0.0, min(1.0, level))
    
    def update(self, dt: float):
        """Update animations"""
        self.animation_time += dt
        self.state_time += dt
        self.emotion_time += dt
        
        # Update blink
        self._update_blink(dt)
        
        # Smooth transitions
        speed = 6.0
        self.current_width += (self.target_width - self.current_width) * speed * dt
        self.current_height += (self.target_height - self.current_height) * speed * dt
        
        # Apply conversation state animations
        self._update_conversation_state(dt)
    
    def _update_blink(self, dt: float):
        """Handle blinking"""
        current_time = self.animation_time
        
        if not self.is_blinking and (current_time - self.last_blink_time) > self.next_blink_interval:
            self.is_blinking = True
            self.blink_start_time = current_time
            self.next_blink_interval = random.uniform(2.5, 5.5)
        
        if self.is_blinking:
            blink_elapsed = current_time - self.blink_start_time
            if blink_elapsed < self.blink_duration / 2:
                self.blink_progress = blink_elapsed / (self.blink_duration / 2)
            elif blink_elapsed < self.blink_duration:
                self.blink_progress = 1 - (blink_elapsed - self.blink_duration / 2) / (self.blink_duration / 2)
            else:
                self.is_blinking = False
                self.blink_progress = 0
                self.last_blink_time = current_time
    
    def _update_conversation_state(self, dt: float):
        """Apply conversation state effects"""
        base_width = self.eye_width
        base_height = self.eye_height
        
        if self.conversation_state == EyeState.LISTENING:
            # Slightly wider when listening
            scale = 1.05 + math.sin(self.animation_time * 3) * 0.02
            self.target_height = base_height * scale
            
        elif self.conversation_state == EyeState.THINKING:
            # Slight squint when thinking
            self.target_height = base_height * 0.85
            
        elif self.conversation_state == EyeState.SPEAKING:
            # Pulse with audio
            pulse = self.audio_level * 0.15
            self.target_height = base_height * (1.0 + pulse)
            self.target_width = base_width * (1.0 + pulse * 0.5)
        else:
            # Idle - gentle breathing
            breath = math.sin(self.animation_time * 1.5) * 0.03
            self.target_height = base_height * (1 + breath)
            self.target_width = base_width
    
    def draw(self, surface: pygame.Surface):
        """Draw both eyes based on current emotion"""
        # Apply blink (reduce height)
        effective_height = self.current_height * (1 - self.blink_progress * 0.9)
        
        # Draw left eye
        self._draw_eye(surface, self.left_eye_x, self.eye_y, 
                      self.current_width, effective_height, is_left=True)
        
        # Draw right eye
        self._draw_eye(surface, self.right_eye_x, self.eye_y,
                      self.current_width, effective_height, is_left=False)
    
    def _draw_eye(self, surface: pygame.Surface, cx: int, cy: int, 
                  width: float, height: float, is_left: bool):
        """Draw a single eye based on emotion state"""
        
        if self.emotion_state == EyeState.HAPPY:
            self._draw_happy_eye(surface, cx, cy, width, height, is_left)
        elif self.emotion_state == EyeState.SAD:
            self._draw_sad_eye(surface, cx, cy, width, height)
        elif self.emotion_state == EyeState.ANGRY:
            self._draw_angry_eye(surface, cx, cy, width, height, is_left)
        elif self.emotion_state == EyeState.SURPRISED:
            self._draw_surprised_eye(surface, cx, cy, width, height)
        else:  # NEUTRAL
            self._draw_neutral_eye(surface, cx, cy, width, height)
    
    def _draw_neutral_eye(self, surface: pygame.Surface, cx: int, cy: int,
                          width: float, height: float):
        """Neutral: Rounded rectangle"""
        rect = pygame.Rect(int(cx - width/2), int(cy - height/2), int(width), int(height))
        corner_radius = int(min(width, height) * 0.15)
        pygame.draw.rect(surface, PINK_PRIMARY, rect, border_radius=corner_radius)
    
    def _draw_happy_eye(self, surface: pygame.Surface, cx: int, cy: int,
                        width: float, height: float, is_left: bool):
        """Happy: Top 2/3 of a pill - rounded top, flat bottom"""
        radius = width / 2
        top_center_y = cy - height/2 + radius
        
        # Create pill shape points for smooth rendering
        points = []
        
        # Top semicircle (more points for smoothness)
        for i in range(25):
            angle = math.pi + (math.pi * i / 24)
            px = cx + math.cos(angle) * radius
            py = top_center_y + math.sin(angle) * radius
            points.append((px, py))
        
        # Bottom corners
        points.append((cx + width/2, cy + height/2))
        points.append((cx - width/2, cy + height/2))
        
        # Draw with anti-aliasing
        int_points = [(int(p[0]), int(p[1])) for p in points]
        pygame.gfxdraw.aapolygon(surface, int_points, PINK_PRIMARY)
        pygame.gfxdraw.filled_polygon(surface, int_points, PINK_PRIMARY)
    
    def _draw_sad_eye(self, surface: pygame.Surface, cx: int, cy: int,
                      width: float, height: float):
        """Sad: Oval/ellipse shape"""
        sad_width = width * 0.8
        sad_height = height * 1.1
        
        pygame.gfxdraw.aaellipse(surface, int(cx), int(cy), 
                                 int(sad_width/2), int(sad_height/2), PINK_PRIMARY)
        pygame.gfxdraw.filled_ellipse(surface, int(cx), int(cy), 
                                      int(sad_width/2), int(sad_height/2), PINK_PRIMARY)
    
    def _draw_angry_eye(self, surface: pygame.Surface, cx: int, cy: int,
                        width: float, height: float, is_left: bool):
        """Angry: Squinted with angled top (20% taller)"""
        angry_height = height * 0.6  # Was 0.5, increased by 20%
        angle_offset = angry_height * 0.4
        
        if is_left:
            points = [
                (cx - width/2, cy - angry_height/2 + angle_offset),
                (cx + width/2, cy - angry_height/2 - angle_offset),
                (cx + width/2, cy + angry_height/2),
                (cx - width/2, cy + angry_height/2),
            ]
        else:
            points = [
                (cx - width/2, cy - angry_height/2 - angle_offset),
                (cx + width/2, cy - angry_height/2 + angle_offset),
                (cx + width/2, cy + angry_height/2),
                (cx - width/2, cy + angry_height/2),
            ]
        
        int_points = [(int(p[0]), int(p[1])) for p in points]
        pygame.gfxdraw.aapolygon(surface, int_points, PINK_PRIMARY)
        pygame.gfxdraw.filled_polygon(surface, int_points, PINK_PRIMARY)
    
    def _draw_surprised_eye(self, surface: pygame.Surface, cx: int, cy: int,
                            width: float, height: float):
        """Surprised: Large circle (reduced by 20% from previous)"""
        size = max(width, height) * 1.25  # 1.56 * 0.8 = 1.248 (20% smaller)
        pygame.gfxdraw.aacircle(surface, int(cx), int(cy), int(size/2), PINK_PRIMARY)
        pygame.gfxdraw.filled_circle(surface, int(cx), int(cy), int(size/2), PINK_PRIMARY)


class DebugLog:
    """Collapsible debug log panel - arrow button in bottom right, expands upward"""
    
    def __init__(self, screen_width: int, screen_height: int, expanded_height: int = 150, max_lines: int = 6):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.expanded_height = expanded_height
        self.max_lines = max_lines
        self.lines: deque = deque(maxlen=max_lines)
        self.font: Optional[pygame.font.Font] = None
        self.line_height = 16
        self._lock = threading.Lock()
        
        # Collapsed state
        self.is_expanded = False
        
        # Button dimensions
        self.button_size = 30
        self.button_rect = pygame.Rect(
            screen_width - self.button_size - 8,
            screen_height - self.button_size - 8,
            self.button_size,
            self.button_size
        )
        
        # Expanded panel rect (calculated when expanded)
        self.panel_rect = pygame.Rect(
            0,
            screen_height - expanded_height,
            screen_width,
            expanded_height
        )
    
    def init_font(self):
        """Initialize font (must be called after pygame.init())"""
        cjk_fonts = [
            'microsoftyahei', 'simhei', 'simsun', 
            'noto sans cjk sc', 'wenquanyi micro hei',
            'arial unicode ms', 'consolas',
        ]
        
        self.font = None
        for font_name in cjk_fonts:
            try:
                self.font = pygame.font.SysFont(font_name, 12)
                if self.font:
                    break
            except:
                continue
        
        if not self.font:
            self.font = pygame.font.Font(None, 14)
    
    def add_line(self, text: str):
        """Add a line to the log"""
        with self._lock:
            self.lines.append(text)
    
    def clear(self):
        """Clear all lines"""
        with self._lock:
            self.lines.clear()
    
    def toggle(self):
        """Toggle expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
    
    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """Check if click is on the toggle button. Returns True if handled."""
        if self.button_rect.collidepoint(pos):
            self.toggle()
            return True
        return False
    
    def draw(self, surface: pygame.Surface):
        """Draw the debug log (collapsed or expanded)"""
        if not self.font:
            self.init_font()
        
        if self.is_expanded:
            self._draw_expanded(surface)
        
        # Always draw the toggle button
        self._draw_button(surface)
    
    def _draw_button(self, surface: pygame.Surface):
        """Draw the toggle button with arrow"""
        # Button background
        pygame.draw.rect(surface, (50, 50, 55), self.button_rect, border_radius=5)
        pygame.draw.rect(surface, (80, 80, 85), self.button_rect, width=1, border_radius=5)
        
        # Arrow (up when collapsed, down when expanded)
        cx, cy = self.button_rect.center
        arrow_size = 8
        
        if self.is_expanded:
            # Down arrow (to collapse)
            points = [
                (cx, cy + arrow_size // 2),
                (cx - arrow_size, cy - arrow_size // 2),
                (cx + arrow_size, cy - arrow_size // 2),
            ]
        else:
            # Up arrow (to expand)
            points = [
                (cx, cy - arrow_size // 2),
                (cx - arrow_size, cy + arrow_size // 2),
                (cx + arrow_size, cy + arrow_size // 2),
            ]
        
        pygame.draw.polygon(surface, (150, 150, 155), points)
    
    def _draw_expanded(self, surface: pygame.Surface):
        """Draw the expanded debug panel"""
        # Draw background
        pygame.draw.rect(surface, DEBUG_BG_COLOR, self.panel_rect)
        pygame.draw.rect(surface, (60, 60, 65), self.panel_rect, 1)
        
        # Draw title
        title = self.font.render("Debug Log (click arrow to close)", True, (100, 100, 105))
        surface.blit(title, (self.panel_rect.x + 8, self.panel_rect.y + 4))
        
        # Draw log lines
        with self._lock:
            y = self.panel_rect.y + 22
            for line in self.lines:
                # Truncate long lines for small screen
                if len(line) > 60:
                    line = line[:57] + "..."
                text_surface = self.font.render(line, True, DEBUG_TEXT_COLOR)
                surface.blit(text_surface, (self.panel_rect.x + 8, y))
                y += self.line_height


class RemyUI:
    """
    Main UI class for Remy AI Desk Companion.
    Manages the pygame window, eyes, and debug log.
    """
    
    def __init__(self, width: int = WINDOW_WIDTH, height: int = WINDOW_HEIGHT):
        self.width = width
        self.height = height
        self.running = False
        
        # Pygame surfaces
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        
        # Fonts (initialized in init())
        self.transcript_font: Optional[pygame.font.Font] = None
        self.state_font: Optional[pygame.font.Font] = None
        
        # Eyes centered in screen
        self.eyes = AnimatedEyes(width // 2, height // 2)
        
        # Collapsible debug log (arrow in bottom right)
        self.debug_log = DebugLog(width, height, expanded_height=120, max_lines=5)
        
        # State display
        self.current_conversation_state = "idle"
        self.current_emotion = "neutral"
        self.user_transcript = ""
        self.ai_transcript = ""
        
        # UI visibility toggle (spacebar)
        self.ui_hidden = False
        
        # Emotion idle timer (revert to neutral after 5s)
        self.last_emotion_time = 0.0
        self.emotion_idle_timeout = 5.0  # seconds
        
        # Emotion buttons for testing (smaller for Pi screen)
        self.emotion_buttons = []
        self._init_emotion_buttons()
    
    def _init_emotion_buttons(self):
        """Initialize emotion test buttons (compact for small screen)"""
        emotions = [
            ("N", EyeState.NEUTRAL, (150, 150, 150)),     # Neutral
            ("H", EyeState.HAPPY, (255, 200, 100)),       # Happy
            ("S", EyeState.SAD, (100, 150, 200)),         # Sad
            ("A", EyeState.ANGRY, (255, 100, 100)),       # Angry
            ("!", EyeState.SURPRISED, (255, 150, 200)),   # Surprised
        ]
        
        button_size = 25
        button_x = self.width - button_size - 5
        button_y = 5
        
        for name, state, color in emotions:
            rect = pygame.Rect(button_x, button_y, button_size, button_size)
            self.emotion_buttons.append({
                "name": name,
                "state": state,
                "rect": rect,
                "color": color,
            })
            button_y += button_size + 3
    
    def init(self):
        """Initialize pygame and create window"""
        pygame.init()
        pygame.display.set_caption("Remy - AI Desk Companion")
        
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.debug_log.init_font()
        
        # Initialize fonts with CJK support for transcripts
        self._init_fonts()
        
        self.running = True
        self.log("UI initialized")
    
    def _init_fonts(self):
        """Initialize fonts with CJK (Chinese/Japanese/Korean) support"""
        # Fonts that support CJK characters
        cjk_fonts = [
            'microsoftyahei',      # Microsoft YaHei (Windows)
            'microsoftyaheui',     # Microsoft YaHei UI
            'simhei',              # SimHei (Windows)
            'simsun',              # SimSun (Windows)
            'noto sans cjk sc',    # Noto Sans CJK (cross-platform)
            'wenquanyi micro hei', # WenQuanYi (Linux)
            'arial unicode ms',    # Arial Unicode
            'arial',               # Fallback
        ]
        
        # Smaller fonts for 3.5" Pi screen
        for font_name in cjk_fonts:
            try:
                self.transcript_font = pygame.font.SysFont(font_name, 12)
                if self.transcript_font:
                    break
            except:
                continue
        
        if not self.transcript_font:
            self.transcript_font = pygame.font.Font(None, 14)
        
        # Even smaller font for state indicator
        for font_name in cjk_fonts:
            try:
                self.state_font = pygame.font.SysFont(font_name, 10)
                if self.state_font:
                    break
            except:
                continue
        
        if not self.state_font:
            self.state_font = pygame.font.Font(None, 12)
    
    def log(self, message: str):
        """Add message to debug log"""
        if DEBUG_MODE:
            self.debug_log.add_line(message)
    
    def set_state(self, state: str):
        """Set the current conversation state (idle, listening, thinking, speaking)"""
        self.eyes.set_state(state)
        self.current_conversation_state = state
    
    def set_audio_level(self, level: float):
        """Set audio level for speaking animation"""
        self.eyes.set_audio_level(level)
    
    def set_user_transcript(self, text: str):
        """Set the current user transcript"""
        self.user_transcript = text
    
    def set_ai_transcript(self, text: str):
        """Set the current AI transcript"""
        self.ai_transcript = text
    
    def set_emotion(self, emotion_name: str, eye_state: str):
        """Set the detected emotion (neutral, happy, sad, angry, surprised)"""
        self.log(f">>> UI set_emotion: {emotion_name} -> {eye_state} <<<")
        self.current_emotion = emotion_name
        self.eyes.set_emotion(eye_state)
        
        # Reset idle timer when setting non-neutral emotion
        if eye_state != EyeState.NEUTRAL:
            self.last_emotion_time = time.time()
    
    def handle_events(self) -> bool:
        """
        Handle pygame events.
        Returns False if window should close.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    # Toggle UI visibility (hide all except eyes)
                    self.ui_hidden = not self.ui_hidden
                    self.log(f"UI {'hidden' if self.ui_hidden else 'visible'}")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = event.pos
                    
                    # Check debug log toggle button first
                    if DEBUG_MODE and self.debug_log.handle_click(mouse_pos):
                        continue
                    
                    # Check emotion button clicks
                    for btn in self.emotion_buttons:
                        if btn["rect"].collidepoint(mouse_pos):
                            self.log(f"Button: {btn['name']}")
                            self.set_emotion(btn["name"], btn["state"])
                            break
        return True
    
    def update(self, dt: float):
        """Update animations"""
        self.eyes.update(dt)
        
        # Revert to neutral emotion after 5s of idle
        if (self.eyes.emotion_state != EyeState.NEUTRAL and 
            self.last_emotion_time > 0 and
            time.time() - self.last_emotion_time > self.emotion_idle_timeout):
            self.log("Emotion timeout - reverting to neutral")
            self.current_emotion = "neutral"
            self.eyes.set_emotion(EyeState.NEUTRAL)
            self.last_emotion_time = 0.0  # Reset timer
    
    def draw(self):
        """Draw the entire UI"""
        if not self.screen:
            return
            
        # Clear screen with background color
        self.screen.fill(BG_COLOR)
        
        # Draw eyes (always visible)
        self.eyes.draw(self.screen)
        
        # Skip drawing other UI elements if hidden (spacebar toggle)
        if self.ui_hidden:
            pygame.display.flip()
            return
        
        # Draw compact state/emotion (top left, single line)
        if self.state_font:
            emotion_colors = {
                "neutral": (150, 150, 150),
                "happy": (255, 200, 100),
                "sad": (100, 150, 200),
                "angry": (255, 100, 100),
                "surprised": (255, 150, 200),
            }
            emotion_color = emotion_colors.get(self.current_emotion, (150, 150, 150))
            
            # Single line: state | emotion
            status_text = self.state_font.render(
                f"{self.current_conversation_state} | {self.current_emotion}", 
                True, emotion_color
            )
            self.screen.blit(status_text, (5, 3))
        
        # Draw transcripts (compact for small screen)
        if self.transcript_font:
            # User transcript at top (green)
            if self.user_transcript:
                display_text = self.user_transcript
                if len(display_text) > 35:
                    display_text = display_text[:32] + "..."
                user_text = self.transcript_font.render(
                    f"You: {display_text}", True, (120, 200, 120)
                )
                self.screen.blit(user_text, (5, 16))
            
            # AI transcript below (pink)
            if self.ai_transcript:
                display_text = self.ai_transcript
                if len(display_text) > 35:
                    display_text = display_text[:32] + "..."
                ai_text = self.transcript_font.render(
                    f"Remy: {display_text}", True, (255, 160, 180)
                )
                self.screen.blit(ai_text, (5, 30))
        
        # Draw emotion buttons (right side)
        self._draw_emotion_buttons()
        
        # Draw debug log (collapsible)
        if DEBUG_MODE:
            self.debug_log.draw(self.screen)
        
        # Update display
        pygame.display.flip()
    
    def _draw_emotion_buttons(self):
        """Draw emotion test buttons on the right side"""
        if not self.state_font:
            return
            
        for btn in self.emotion_buttons:
            rect = btn["rect"]
            color = btn["color"]
            is_selected = btn["name"] == self.current_emotion
            
            # Draw button background
            if is_selected:
                # Selected button - filled with color
                pygame.draw.rect(self.screen, color, rect, border_radius=5)
                text_color = (40, 40, 45)
            else:
                # Unselected - outline only
                pygame.draw.rect(self.screen, (60, 60, 65), rect, border_radius=5)
                pygame.draw.rect(self.screen, color, rect, width=2, border_radius=5)
                text_color = color
            
            # Draw button text
            text = self.state_font.render(btn["name"], True, text_color)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
    
    def run_frame(self) -> bool:
        """
        Run a single frame.
        Returns False if window should close.
        """
        if not self.running:
            return False
            
        # Handle events
        if not self.handle_events():
            self.running = False
            return False
        
        # Calculate delta time
        dt = self.clock.tick(FPS) / 1000.0
        
        # Update and draw
        self.update(dt)
        self.draw()
        
        return True
    
    def quit(self):
        """Clean up pygame"""
        self.running = False
        pygame.quit()


# Test the UI independently
if __name__ == "__main__":
    ui = RemyUI()
    ui.init()
    
    # Test state cycling
    states = [EyeState.IDLE, EyeState.LISTENING, EyeState.THINKING, EyeState.SPEAKING]
    state_idx = 0
    last_state_change = time.time()
    
    ui.log("Testing eye animations...")
    ui.log("Click emotion buttons to test!")
    ui.log("Press ESC to exit")
    
    while ui.running:
        # Cycle conversation states every 3 seconds
        if time.time() - last_state_change > 3:
            state_idx = (state_idx + 1) % len(states)
            ui.set_state(states[state_idx])
            ui.log(f"Changed state to: {states[state_idx]}")
            last_state_change = time.time()
        
        # Simulate audio level when speaking
        if ui.eyes.conversation_state == EyeState.SPEAKING:
            level = (math.sin(time.time() * 10) + 1) / 2 * 0.8
            ui.set_audio_level(level)
        
        if not ui.run_frame():
            break
    
    ui.quit()
