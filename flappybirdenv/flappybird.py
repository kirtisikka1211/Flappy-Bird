import pygame
import random
from pygame.locals import *
from .AllComponents import *
from .flappybird_constants import *



class FlappyBird():
    def __init__(self):
        #initializing  pygame's resources
        pygame.init()
        pygame.mixer.init()
        pygame.font.init()
        current_dir = os.path.dirname(os.path.abspath(__file__))

        #game window initialized
        self.screen = pygame.display.set_mode((SCREEN_WIDHT, SCREEN_HEIGHT))
        pygame.display.set_caption('Flappy Bird')
        pygame.mixer.set_num_channels(10)

        #defining positions for score and epoch number
        self.score_pos = (SCREEN_WIDHT // 2 - font.get_height() // 2, SCREEN_HEIGHT//20)
        self.epoch_pos = (SCREEN_WIDHT // 18 - font.get_height() // 2, SCREEN_HEIGHT//20)

        #loading backgrounds for normal and dark realm
        self.backgrounds = {
            'day': pygame.transform.scale(pygame.image.load(os.path.join(current_dir, "assets", "sprites","background-day.png")), (SCREEN_WIDHT, SCREEN_HEIGHT)),
            'night': pygame.transform.scale(pygame.image.load(os.path.join(current_dir, "assets", "sprites","99940c9c-80ca-4f15-beef-d507c044e1d4.jpg")), (SCREEN_WIDHT, SCREEN_HEIGHT))
        }
        self.current_bg = 'day'
        self.BACKGROUND = self.backgrounds[self.current_bg]

        #initializing sprite groups for the game to display
        self.pipe_group = pygame.sprite.Group()
        self.reward_group = pygame.sprite.Group()
        self.portal_group = pygame.sprite.Group()
        self.crystal_group = pygame.sprite.Group()
        self.spike_group = pygame.sprite.Group()
        self.ground_group = pygame.sprite.Group()
        self.bird_group = pygame.sprite.Group()
        self.top_boundary = TopBoundary()
        
        #setting parameters for the portals, starting at normal realm
        self.portal_mode = False
        self.portal_timer = 0
        self.portal_duration = 120

        #initializing flappy and add it to the bird group, starting the bird on the left hand side of the screen at a predefined height
        self.bird = Bird()
        self.bird_group.add(self.bird)
        self.bird.begin()

        #initializing the ground sprite, pipes, score and time
        for i in range (2):
            ground = Ground(GROUND_WIDHT * i)
            self.ground_group.add(ground) 

        self._spawnFirstPipes()

        self.score = 0

        self.clock = pygame.time.Clock()

    #updates the parameters according to user input
    def update_config(self, pipe_prob=None, pipe_spacing=None, num_portals=None, crystal_prob=None, max_steps=None):
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


    #maing the first 3 pipes and rewards at predefined locations at the start
    def _spawnFirstPipes(self):
        for i in range (3):
            pos =  250 * i + 400 
            pipesAndReward = self._getRandomPipesAndReward(pos)
            self.pipe_group.add(pipesAndReward[0])
            self.pipe_group.add(pipesAndReward[1])
            self.reward_group.add(pipesAndReward[2])
            if pipesAndReward[3]:
                self.portal_group.add(pipesAndReward[3])


    #generating random pipe and reward at a predefined position
    def _getRandomPipesAndReward(self, xpos):
        size = random.randint(100, 350)
        #using pipe_prob from cofiguation, keeping initial probabilities as 0.3
        has_portal = random.random() < getattr(self, 'pipe_prob', 0.3)

        pipe = Pipe(False, xpos, size, has_portal)
        pipe_inverted = Pipe(True, xpos, SCREEN_HEIGHT - size - PIPE_GAP, has_portal)
        reward = Reward(xpos + PIPE_WIDHT/2)

        portal = None
        if has_portal:
            portal_y = SCREEN_HEIGHT - size - PIPE_GAP//2 - 30
            portal = Portal(xpos + PIPE_WIDHT//2 - 20, portal_y)

        return pipe, pipe_inverted, reward, portal

    

    def _spawnCrystals(self):
        self.crystal_group.empty()
        self.spike_group.empty()
        for i in range(10):
            pos = 100 * i + 400
            crystal = Crystal(pos, random.randint(150, 350))
            self.crystal_group.add(crystal)
            
            #adding spikes between the crystals
            if i % 3 == 1:
                spike = Spike(pos - 50, random.randint(200, 400))
                self.spike_group.add(spike)

    #resets the game to the starting positions for the basic objects
    def resetGame(self):
        # empty groups
        self.pipe_group.empty()
        self.reward_group.empty()
        self.portal_group.empty()
        self.crystal_group.empty()
        self.spike_group.empty()

        #resetting background and portal mode when it restarts
        self.current_bg = 'day'
        self.BACKGROUND = self.backgrounds[self.current_bg]
        self.portal_mode = False
        self.portal_timer = 0

        #making new pipes, reseting bird's position and score
        self._spawnFirstPipes()
        self.bird.begin()
        self.score = 0


    #gives the game's current state
    def getGameState(self):
        state_params = []

        if self.portal_mode and self.crystal_group.sprites():
            #in portal mode: use crystal positions
            nearest_crystal = self.crystal_group.sprites()[0]
            obstacle_x = nearest_crystal.rect[0] - self.bird.rect[0]
            obstacle_top_y = nearest_crystal.rect[1]
            obstacle_bottom_y = nearest_crystal.rect[1] + 80  #defining crystal's height
        else:
            #in normal mode: use pipe positions
            if not self.pipe_group.sprites():
                return [0.0, 0.0, 1.0, self.bird.rect[1] / SCREEN_HEIGHT, (self.bird.speed + MAXSPEED) / (2 * MAXSPEED)]
            
            chosenpipeindex = 0
            nextpipe_x = self.pipe_group.sprites()[chosenpipeindex].rect[0] + PIPE_WIDHT
            if (nextpipe_x < self.bird.rect[0]):
                chosenpipeindex = 2

            obstacle_x = self.pipe_group.sprites()[chosenpipeindex].rect[0] - self.bird.rect[0]
            obstacle_bottom_y = self.pipe_group.sprites()[chosenpipeindex].rect[1]
            obstacle_top_y = obstacle_bottom_y - PIPE_GAP

        #normalizing the state's values for better visibility
        obstacle_top_y_norm = obstacle_top_y / SCREEN_HEIGHT
        obstacle_bottom_y_norm = obstacle_bottom_y / SCREEN_HEIGHT
        obstacle_x_norm = max(0, min(1, (obstacle_x + 200) / 1200))
        bird_y_norm = self.bird.rect[1] / SCREEN_HEIGHT
        bird_speed_norm = (self.bird.speed + MAXSPEED) / (2 * MAXSPEED)

        state_params.append(obstacle_top_y_norm)
        state_params.append(obstacle_bottom_y_norm)
        state_params.append(obstacle_x_norm)
        state_params.append(bird_y_norm)
        state_params.append(bird_speed_norm)

        return state_params
    
    #move the game by 1 frame
    def _handleEvents(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()

    #takes one action and advances the game by 1 state/frame
    def step(self, action=None, epoch=-1):
        #ticks pygame clock and reset variables 
        self.clock.tick_busy_loop(30)
        gameOver = gotReward = False

        #render epoch if necessary and the score
        display_score = font.render(str(self.score), True, (255, 255, 255))
        display_epoch = font2.render(f"epoch: {epoch}", True, (255, 255, 255))

        #calling to move the game to next frame
        self._handleEvents()

        #then take the action
        if action == 1:
            self.bird.bump()

        elif action is None:
            raise Exception("no action")


        #checking if the ground sprite is off screen and update it
        if is_off_screen(self.ground_group.sprites()[0]):
            self.ground_group.remove(self.ground_group.sprites()[0])

            new_ground = Ground(GROUND_WIDHT - 20)
            self.ground_group.add(new_ground)

        #making new obstacles based on mode
        if self.portal_mode:
            #it should be crystals in portal mode
            if self.crystal_group.sprites() and is_off_screen(self.crystal_group.sprites()[0]):
                self.crystal_group.remove(self.crystal_group.sprites()[0])
                #make multiple crystals for more challenge
                crystal1 = Crystal(DEFAULT_PIPE_SPAWN_POINT, random.randint(120, 200))
                crystal2 = Crystal(DEFAULT_PIPE_SPAWN_POINT + 80, random.randint(350, 430))
                self.crystal_group.add(crystal1)
                self.crystal_group.add(crystal2)
        else:
            #pipes in normal mode
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

        #call the update() method for each of the sprite group objects to update their positions
        self.bird_group.update()
        self.ground_group.update()
        if self.portal_mode:
            self.crystal_group.update()
            self.spike_group.update()
        else:
            self.pipe_group.update()
        self.reward_group.update()
        self.portal_group.update()

        #draw the background
        self.screen.blit(self.BACKGROUND, (0, 0))

        #call the draw() method for each of the sprite group objects and draw them on the screen
        self.bird_group.draw(self.screen)
        if self.portal_mode:
            self.crystal_group.draw(self.screen)
            self.spike_group.draw(self.screen)
        else:
            self.pipe_group.draw(self.screen)
        self.ground_group.draw(self.screen)
        self.reward_group.draw(self.screen)
        self.portal_group.draw(self.screen)

        #display the score, epoch and top boundary.
        self.screen.blit(display_score, self.score_pos)
        self.screen.blit(display_epoch, self.epoch_pos)
        self.screen.blit(self.top_boundary.surf, (0, -4))

        #check crystal collection is happening in portal mode
        crystal_reward = False
        if self.portal_mode:
            if pygame.sprite.groupcollide(self.bird_group, self.crystal_group, False, True, pygame.sprite.collide_mask):
                pygame.mixer.find_channel().play(point_sound)
                self.score += 1
                crystal_reward = True
                #make a new crystal
                crystal1 = Crystal(DEFAULT_PIPE_SPAWN_POINT, random.randint(120, 200))
                crystal2 = Crystal(DEFAULT_PIPE_SPAWN_POINT + 60, random.randint(350, 430))
                spike = Spike(DEFAULT_PIPE_SPAWN_POINT + 30, random.randint(250, 300))
                self.crystal_group.add(crystal1)
                self.crystal_group.add(crystal2)
                self.spike_group.add(spike)
            
            #check if it collided with spike, if yes, then end the mode in the next frame
            if pygame.sprite.groupcollide(self.bird_group, self.spike_group, False, False, pygame.sprite.collide_mask):
                self.portal_mode = False
                self.current_bg = 'day'
                self.BACKGROUND = self.backgrounds[self.current_bg]
                self.crystal_group.empty()
                self.spike_group.empty()
                self._spawnFirstPipes()

        #checking if it collided with obstacles
        obstacle_collision = (pygame.sprite.groupcollide(self.bird_group, self.ground_group, False, False, pygame.sprite.collide_mask) or
                              pygame.sprite.collide_mask(self.bird, self.top_boundary))

        if not self.portal_mode:
            obstacle_collision = (obstacle_collision or
                                  pygame.sprite.groupcollide(self.bird_group, self.pipe_group, False, False, pygame.sprite.collide_mask))

        if obstacle_collision:
            pygame.mixer.find_channel().play(die_sound)
            gameOver = True

        #did the bird get a reward?
        if (pygame.sprite.groupcollide(self.bird_group, self.reward_group, False, False, pygame.sprite.collide_mask)):
            self.reward_group.remove(self.reward_group.sprites()[0])
            pygame.mixer.find_channel().play(point_sound)
            self.score += 1
            gotReward = True
        
        #did the bird enter a portal
        portal_reward = False
        if (pygame.sprite.groupcollide(self.bird_group, self.portal_group, False, True, pygame.sprite.collide_mask)):
            self.portal_mode = True
            self.portal_timer = self.portal_duration
            self.current_bg = 'night'
            self.BACKGROUND = self.backgrounds[self.current_bg]
            #if yes, just swap pipes with crystals
            self.pipe_group.empty()
            self.reward_group.empty()
            self._spawnCrystals()
            portal_reward = True
        
        #handling timer for portal mode
        if self.portal_mode:
            self.portal_timer -= 1
            if self.portal_timer <= 0:
                self.portal_mode = False
                self.current_bg = 'day'
                self.BACKGROUND = self.backgrounds[self.current_bg]
                # Restore normal pipes
                self.crystal_group.empty()
                self._spawnFirstPipes()

        #updating entire game display
        pygame.display.update()
            
        return gameOver, gotReward, portal_reward, crystal_reward