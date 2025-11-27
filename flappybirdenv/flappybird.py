import pygame
import random
import math
from pygame.locals import *
from .AllComponents import *
from .flappybird_constants import *



class FlappyBird():
    def __init__(self):
        #initialize pygame resources
        pygame.init()
        pygame.mixer.init()
        pygame.font.init()
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # initialize game window 
        self.screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))
        pygame.display.set_caption('Flappy Bird')
        pygame.mixer.set_num_channels(10)

        # constant score and epoch positions
        self.score_pos = (SCREEN_WIDHT // 2 - font.get_height() // 2, SCREEN_HEIGHT//20)
        self.epoch_pos = (SCREEN_WIDHT // 18 - font.get_height() // 2, SCREEN_HEIGHT//20)

        # load backgrounds
        self.backgrounds = {
            'day': pygame.transform.scale(pygame.image.load(os.path.join(current_dir, "assets", "sprites","background-day.png")), (SCREEN_WIDHT, SCREEN_HEIGHT)),
            'night': pygame.transform.scale(pygame.image.load(os.path.join(current_dir, "assets", "sprites","background-night.png")), (SCREEN_WIDHT, SCREEN_HEIGHT))
        }
        # Create portal realm background
        self.portal_bg = pygame.Surface((SCREEN_WIDHT, SCREEN_HEIGHT))
        self.portal_bg.fill((20, 0, 40))  # Dark purple
        self.current_bg = 'day'
        self.BACKGROUND = self.backgrounds[self.current_bg]
        
        # Portal mode state
        self.portal_mode = False
        self.portal_timer = 0
        self.portal_duration = 300  # frames
        self.crystal_group = pygame.sprite.Group()

        # initialize essential groups to store game objects
        self.pipe_group = pygame.sprite.Group()
        self.reward_group = pygame.sprite.Group()
        self.portal_group = pygame.sprite.Group()
        self.ground_group = pygame.sprite.Group()
        self.bird_group = pygame.sprite.Group()
        self.top_boundary = TopBoundary()

        # initialize bird and add it to the bird group
        self.bird = Bird()
        self.bird_group.add(self.bird)
        # spawn bird on the left hand side of the screen at a predefined height
        self.bird.begin()

        # initialize ground sprites
        for i in range (2):
            ground = Ground(GROUND_WIDHT * i)
            self.ground_group.add(ground) 

        # initialize pipes and reward groups
        self._spawnFirstPipes()

        # start score at 0
        self.score = 0

        self.clock = pygame.time.Clock()

    # Spawn the first 3 pipes and rewards at predefined locations
    def _spawnFirstPipes(self):
        for i in range (3):  # spawn 3 pipes
            pos =  250 * i + 400  # spawn locations
            pipesAndReward = self._getRandomPipesAndReward(pos)  # generate pipes at random heights
            self.pipe_group.add(pipesAndReward[0])
            self.pipe_group.add(pipesAndReward[1])
            self.reward_group.add(pipesAndReward[2])
            if pipesAndReward[3]:  # portal exists
                self.portal_group.add(pipesAndReward[3])


    # Generate random pipe and reward at a predefined position
    def _getRandomPipesAndReward(self, xpos):
        # chooses a random pipe height 
        size = random.randint(100, 350)
        has_portal = random.randint(1, 10) <= 3  # 30% chance

        # Create pipes and a reward
        pipe = Pipe(False, xpos, size, has_portal)
        pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP, has_portal)
        reward = Reward(xpos + PIPE_WIDHT/2)
        
        portal = None
        if has_portal:
            portal_y = SCREEN_HEIGHT - size - PIPE_GAP//2 - 30
            portal = Portal(xpos + PIPE_WIDHT//2 - 20, portal_y)

        return pipe, pipe_inverted, reward, portal
    
    def _spawnCrystals(self):
        for i in range(3):
            pos = 250 * i + 400
            crystal = Crystal(pos, random.randint(100, 400))
            self.crystal_group.add(crystal)

    # resets the game to the starting positions for the necessary objects
    def resetGame(self):
        # empty groups
        self.pipe_group.empty()
        self.reward_group.empty()
        self.portal_group.empty()

        # reset background and portal mode
        self.current_bg = 'day'
        self.BACKGROUND = self.backgrounds[self.current_bg]
        self.portal_mode = False
        self.portal_timer = 0
        self.crystal_group.empty()

        # spawn new pipes
        self._spawnFirstPipes()
        # reset bird's position
        self.bird.begin()
        #reset score
        self.score = 0


    # returns the current game state (normalized)
    def getGameState(self):
        state_params = []

        if self.portal_mode and self.crystal_group.sprites():
            # Portal mode: use crystal positions
            nearest_crystal = self.crystal_group.sprites()[0]
            obstacle_x = nearest_crystal.rect[0] - self.bird.rect[0]
            obstacle_top_y = nearest_crystal.rect[1]
            obstacle_bottom_y = nearest_crystal.rect[1] + 80  # Crystal height
            obstacle_middle_y = obstacle_top_y + 40
        else:
            # Normal mode: use pipe positions
            if not self.pipe_group.sprites():
                # Normalize default state (no pipes ahead)
                return [0.0, 0.0, 1.0, self.bird.rect[1] / SCREEN_HEIGHT, (self.bird.speed + MAXSPEED) / (2 * MAXSPEED)]
            
            chosenpipeindex = 0
            nextpipe_x = self.pipe_group.sprites()[chosenpipeindex].rect[0] + PIPE_WIDHT
            if (nextpipe_x < self.bird.rect[0]):
                chosenpipeindex = 2

            obstacle_x = self.pipe_group.sprites()[chosenpipeindex].rect[0] - self.bird.rect[0]
            obstacle_bottom_y = self.pipe_group.sprites()[chosenpipeindex].rect[1]
            obstacle_top_y = obstacle_bottom_y - PIPE_GAP
            obstacle_middle_y = obstacle_bottom_y - (PIPE_GAP / 2)

        # Normalize state values to [0, 1] range for better neural network learning
        # Normalize obstacle positions relative to screen height
        obstacle_top_y_norm = obstacle_top_y / SCREEN_HEIGHT
        obstacle_bottom_y_norm = obstacle_bottom_y / SCREEN_HEIGHT
        
        # Normalize horizontal distance to pipe (crucial for timing jumps)
        # obstacle_x: negative = pipe behind bird, positive = pipe ahead
        # Normalize to [0, 1] where 0 = pipe far behind, 0.5 = pipe at bird, 1 = pipe far ahead
        # Use a more meaningful range: pipes typically spawn 400-1050 pixels ahead
        # Normalize so that 0 = -200 (behind), 1 = 1000 (far ahead)
        obstacle_x_norm = max(0, min(1, (obstacle_x + 200) / 1200))
        
        # Normalize bird's vertical position
        bird_y_norm = self.bird.rect[1] / SCREEN_HEIGHT
        
        # Normalize bird speed (speed ranges from -MAXSPEED to MAXSPEED)
        bird_speed_norm = (self.bird.speed + MAXSPEED) / (2 * MAXSPEED)

        # compile the state parameters (all normalized)
        # State: [obstacle_top_y, obstacle_bottom_y, obstacle_x, bird_y, bird_speed]
        state_params.append(obstacle_top_y_norm)
        state_params.append(obstacle_bottom_y_norm)
        state_params.append(obstacle_x_norm)
        state_params.append(bird_y_norm)
        state_params.append(bird_speed_norm)

        return state_params
    
    # Advance the game by 1 frame
    def _handleEvents(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()

    # takes one action and advances the game by 1 step (1 frame)
    def step(self, action=None, epoch=-1):
        # tick pygame clock and reset variables 
        self.clock.tick_busy_loop(30)
        gameOver = gotReward = False

        # render epoch if necessary and the score
        display_score = font.render(str(self.score), True, (255, 255, 255))
        display_epoch = font2.render(f"epoch: {epoch}", True, (255, 255, 255))

        # handle user events
        self._handleEvents()

        # take action
        if action == 1:
            self.bird.bump()

        elif action is None:
            raise Exception("no action")


        # check if the ground sprite is off screen and update it
        if is_off_screen(self.ground_group.sprites()[0]):
            self.ground_group.remove(self.ground_group.sprites()[0])

            new_ground = Ground(GROUND_WIDHT - 20)
            self.ground_group.add(new_ground)

        # Spawn new obstacles based on mode
        if self.portal_mode:
            # Spawn crystals in portal mode
            if self.crystal_group.sprites() and is_off_screen(self.crystal_group.sprites()[0]):
                self.crystal_group.remove(self.crystal_group.sprites()[0])
                new_crystal = Crystal(DEFAULT_PIPE_SPAWN_POINT, random.randint(100, 400))
                self.crystal_group.add(new_crystal)
        else:
            # Spawn pipes in normal mode
            if self.pipe_group.sprites() and is_off_screen(self.pipe_group.sprites()[0]):
                self.pipe_group.remove(self.pipe_group.sprites()[0])
                self.pipe_group.remove(self.pipe_group.sprites()[0])
                if self.reward_group.sprites():
                    self.reward_group.remove(self.reward_group.sprites()[0])

                pipesAndReward = self._getRandomPipesAndReward(DEFAULT_PIPE_SPAWN_POINT)

                self.pipe_group.add(pipesAndReward[0])
                self.pipe_group.add(pipesAndReward[1])
                self.reward_group.add(pipesAndReward[2])
                if pipesAndReward[3]:
                    self.portal_group.add(pipesAndReward[3])

        # Call the update() method for each of the sprite group objects, which updates their positions
        if self.portal_mode:
            self.bird.update_portal()
        else:
            self.bird_group.update()
        self.ground_group.update()
        if self.portal_mode:
            self.crystal_group.update()
        else:
            self.pipe_group.update()
        self.reward_group.update()
        self.portal_group.update()

        # draw the background
        self.screen.blit(self.BACKGROUND, (0, 0))
        
        # Add portal realm effects
        if self.portal_mode:
            # Floating stars effect
            for i in range(20):
                x = (i * 50 + self.portal_timer) % SCREEN_WIDHT
                y = (i * 30 + self.portal_timer // 2) % SCREEN_HEIGHT
                pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 2)
            # Energy waves
            for i in range(0, SCREEN_WIDHT, 40):
                wave_y = SCREEN_HEIGHT // 2 + 50 * math.sin((self.portal_timer + i) * 0.1)
                pygame.draw.circle(self.screen, (100, 255, 255), (i, int(wave_y)), 10)

        # Call the draw() method for each of the sprite group objects and draw them on the screen
        self.bird_group.draw(self.screen)
        if self.portal_mode:
            self.crystal_group.draw(self.screen)
        else:
            self.pipe_group.draw(self.screen)
        self.ground_group.draw(self.screen)
        self.reward_group.draw(self.screen)
        self.portal_group.draw(self.screen)

        # Display the score, epoch and top boundary.
        self.screen.blit(display_score, self.score_pos)
        self.screen.blit(display_epoch, self.epoch_pos)
        self.screen.blit(self.top_boundary.surf, (0, -4))

        # Check for collisions
        obstacles = self.crystal_group if self.portal_mode else self.pipe_group
        if (pygame.sprite.groupcollide(self.bird_group, self.ground_group, False, False, pygame.sprite.collide_mask) or
                pygame.sprite.groupcollide(self.bird_group, obstacles, False, False, pygame.sprite.collide_mask) or
                pygame.sprite.collide_mask(self.bird, self.top_boundary)):
            gameOver = True

        # Check if the bird has captured a reward
        if (pygame.sprite.groupcollide(self.bird_group, self.reward_group, False, False, pygame.sprite.collide_mask)):
            # remove the captured reward object from game
            self.reward_group.remove(self.reward_group.sprites()[0])

            # play point sound
            pygame.mixer.find_channel().play(point_sound)

            # increment score
            self.score += 1

            # set gotReward to true
            gotReward = True
        
        # Check if bird enters portal
        portal_reward = False
        if (pygame.sprite.groupcollide(self.bird_group, self.portal_group, False, True, pygame.sprite.collide_mask)):
            # Enter portal realm - completely different world
            self.portal_mode = True
            self.portal_timer = self.portal_duration
            self.BACKGROUND = self.portal_bg
            # Replace pipes with crystals
            self.pipe_group.empty()
            self._spawnCrystals()
            portal_reward = True
        
        # Handle portal mode
        if self.portal_mode:
            self.portal_timer -= 1
            if self.portal_timer <= 0:
                self.portal_mode = False
                self.current_bg = 'day'
                self.BACKGROUND = self.backgrounds[self.current_bg]
                # Restore normal pipes
                self.crystal_group.empty()
                self._spawnFirstPipes()

        # update entire game display
        pygame.display.update()
            
        return gameOver, gotReward, portal_reward