import pygame, random
from .flappybird_constants import *
import os

#Paths
current_dir = os.path.dirname(os.path.abspath(__file__))

wing_path = os.path.join(current_dir,"assets", "audio", "wing.wav")
hit_path = os.path.join(current_dir,"assets", "audio", "hit.wav")
point_path = os.path.join(current_dir,"assets", "audio", "point.wav")
die_path = os.path.join(current_dir,"assets", "audio", "die.ogg")
font_path = os.path.join(current_dir,"assets", "flappy-bird-font.ttf")
bird_upflap_path = os.path.join(current_dir,"assets", "sprites", "yellowbird-upflap.png")
bird_midflap_path = os.path.join(current_dir,"assets", "sprites", "yellowbird-midflap.png")
bird_downflap_path = os.path.join(current_dir,"assets", "sprites", "yellowbird-downflap.png")
pipe_green_path = os.path.join(current_dir,"assets", "sprites", "pipe-green.png")
pipe_red_path = os.path.join(current_dir,"assets", "sprites", "pipe-red.png")
base_path = os.path.join(current_dir,"assets", "sprites", "base.png")

pygame.init()
pygame.mixer.init()
pygame.font.init()
font = pygame.font.Font(font_path, 42)
font2 = pygame.font.Font(font_path, 28)

wing_sound = pygame.mixer.Sound(wing_path)
hit_sound = pygame.mixer.Sound(hit_path)
point_sound = pygame.mixer.Sound(point_path)
die_sound = pygame.mixer.Sound(die_path)

class Bird(pygame.sprite.Sprite):

    def __init__(self):
        super().__init__()

        self.images =  [pygame.image.load(bird_upflap_path).convert_alpha(),
                        pygame.image.load(bird_midflap_path).convert_alpha(),
                        pygame.image.load(bird_downflap_path).convert_alpha()]

        self.speed = SPEED

        self.current_image = 0
        self.image = self.images[0]
        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2.5

        self.current_angle = 0

    def update(self):
        self.current_image = (self.current_image + 1) % 3
        self.image = self.images[self.current_image]
        self.image = pygame.transform.rotate(self.image, 30)
        self.speed += GRAVITY
        if self.speed > MAXSPEED:
            self.speed = MAXSPEED
        self.current_angle = (self.current_angle - 4) if (self.current_angle > -90) else -90

        self.image = pygame.transform.rotate(self.image, self.current_angle)
        # self.rect = self.image.get_rect(center=self.rect.center)

        #UPDATE HEIGHT
        self.rect[1] += self.speed

        def update_config(self, pipe_prob=None, pipe_spacing=None, num_portals=None, crystal_prob=None, max_steps=None):
            """
            Update game configuration dynamically.
            """
            if pipe_prob is not None:
                self.pipe_prob = pipe_prob
            if pipe_spacing is not None:
                self.pipe_spacing = pipe_spacing
            if num_portals is not None:
                self.num_portals = num_portals
            if crystal_prob is not None:
                self.crystal_prob = crystal_prob
            if max_steps is not None:
                self.max_steps = max_steps

    def bump(self):
        self.current_angle = 30
        self.image = pygame.transform.rotate(self.image, self.current_angle)
        # self.rect = self.image.get_rect(center=self.rect.center)
        self.speed = -SPEED

        # make sure bird doesn't fly above the boundaries of the screen
        if self.rect[1] < 0 :
            self.rect[1] = 0

    def begin(self):
        self.rect[0] = SCREEN_WIDHT / 6
        self.rect[1] = SCREEN_HEIGHT / 2.5
        self.current_image = (self.current_image + 1) % 3
        self.current_angle = 0
        self.speed = 0  # Start with zero speed
        self.image = self.images[self.current_image]
        self.image = pygame.transform.rotate(self.image, self.current_angle)



class Pipe(pygame.sprite.Sprite):

    def __init__(self, inverted, xpos, ysize, has_portal=False):
        super().__init__()

        pipe_path = pipe_red_path if has_portal else pipe_green_path
        self.image = pygame.image.load(pipe_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (PIPE_WIDHT, PIPE_HEIGHT))
        self.has_portal = has_portal

        self.rect = self.image.get_rect()
        self.rect[0] = xpos

        if inverted:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect[1] = - (self.rect[3] - ysize)
        else:
            self.rect[1] = SCREEN_HEIGHT - ysize


        self.mask = pygame.mask.from_surface(self.image)


    def update(self):
        self.rect[0] -= GAME_SPEED


# class Score():
#     def __init__(self):
#         self.score = 0
#         self.pos = (SCREEN_WIDHT // 2 - font.get_height() // 2, SCREEN_HEIGHT//20)


#     def update(self, new_val):
#         self.score = new_val
#         score_disp = font.render(str(new_val), True, (255, 255, 255))
#         return score_disp
    

class TopBoundary(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.surf = pygame.Surface((SCREEN_WIDHT, 1))
        self.surf.fill((255, 255, 255))
        self.surf.set_alpha(0)

        self.rect = self.surf.get_rect()

        self.mask = pygame.mask.from_surface(self.surf)

        # self.rect[0] = 0
        # self.rect[1] = 0


class Reward(pygame.sprite.Sprite):
    def __init__(self, xpos):
        super().__init__()
        self.surf = pygame.Surface((3, SCREEN_HEIGHT - GROUND_HEIGHT))
        self.surf.fill((255, 255, 255))
        self.surf.set_alpha(0)  # Makes it invisible
          
        self.rect = self.surf.get_rect()
        self.rect[0] = xpos

        self.mask = pygame.mask.from_surface(self.surf)

        self.image = self.surf

        self.initial_xpos = xpos


    def get_position(self):
        return (self.rect[0], self.rect[1])
    
    def update(self):
        self.rect[0] -= GAME_SPEED

    def reset(self):
        self.rect[0] = SCREEN_WIDHT * 2


class Portal(pygame.sprite.Sprite):
    def __init__(self, xpos, ypos):
        super().__init__()
        self.image = pygame.Surface((40, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (138, 43, 226), (5, 10, 30, 40))
        pygame.draw.ellipse(self.image, (75, 0, 130), (10, 15, 20, 30))
        pygame.draw.ellipse(self.image, (0, 0, 0), (15, 20, 10, 20))
        
        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = ypos
        
        self.mask = pygame.mask.from_surface(self.image)
    
    def update(self):
        self.rect[0] -= GAME_SPEED


class Crystal(pygame.sprite.Sprite):
    def __init__(self, xpos, ypos):
        super().__init__()
        self.image = pygame.Surface((40, 50), pygame.SRCALPHA)  # Smaller
        # Draw crystal shape
        points = [(20, 5), (35, 20), (30, 45), (10, 45), (5, 20)]
        pygame.draw.polygon(self.image, (0, 255, 255), points)
        pygame.draw.polygon(self.image, (100, 200, 255), points, 2)
        
        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = ypos
        self.mask = pygame.mask.from_surface(self.image)
        
        self.base_y = ypos
        self.move_counter = random.randint(0, 360)
        
    def update(self):
        self.rect[0] -= GAME_SPEED * 2  # Much faster in portal
        
        # Vertical oscillation
        self.move_counter += 3
        import math
        self.rect[1] = self.base_y + 25 * math.sin(math.radians(self.move_counter))


class Ground(pygame.sprite.Sprite):
    def __init__(self, xpos):
        super().__init__()
        self.image = pygame.image.load(base_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (GROUND_WIDHT, GROUND_HEIGHT))

        self.mask = pygame.mask.from_surface(self.image)

        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT

    def update(self):
        self.rect[0] -= GAME_SPEED


class Spike(pygame.sprite.Sprite):
    def __init__(self, xpos, ypos):
        super().__init__()
        self.image = pygame.Surface((30, 40), pygame.SRCALPHA)
        # Draw spike shape
        points = [(15, 0), (25, 35), (5, 35)]
        pygame.draw.polygon(self.image, (255, 50, 50), points)
        pygame.draw.polygon(self.image, (200, 0, 0), points, 2)
        
        self.rect = self.image.get_rect()
        self.rect[0] = xpos
        self.rect[1] = ypos
        self.mask = pygame.mask.from_surface(self.image)
        
    def update(self):
        self.rect[0] -= GAME_SPEED * 2.5


def is_off_screen(sprite):
    return sprite.rect[0] < -(sprite.rect[2])


# will be implemented in flappybird.py
def _getRandomPipesAndReward(self, xpos):
    size = random.randint(100, 350)
    has_portal = random.random() < getattr(self, 'pipe_prob', 0.3)  # default 30%
    
    pipe = Pipe(False, xpos, size, has_portal)
    pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP, has_portal)
    reward = Reward(xpos + PIPE_WIDHT / 2)
    
    portal = None
    if has_portal:
        portal_y = SCREEN_HEIGHT - size - PIPE_GAP // 2 - 30
        portal = Portal(xpos + PIPE_WIDHT // 2 - 20, portal_y)
    
    return pipe, pipe_inverted, reward, portal



    