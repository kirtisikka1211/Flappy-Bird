import pygame
from pygame.locals import *
from flappybirdenv.flappybird import FlappyBird

def main():
    # Initialize the game
    game = FlappyBird()
    
    print("Manual Flappy Bird Controls:")
    print("- SPACE or UP ARROW: Jump")
    print("- ESC: Quit")
    print("- Enter portals to collect crystals!")
    
    running = True
    clock = pygame.time.Clock()
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE or event.key == K_UP:
                    # Jump action
                    action = 1
                else:
                    action = 0
            else:
                action = 0
        
        # Step the game
        try:
            gameOver, gotReward, portal_reward, crystal_reward = game.step(action, 0)
            
            # Print rewards
            if gotReward:
                print(f"Pipe passed! Score: {game.score}")
            if portal_reward:
                print("Entered portal realm!")
            if crystal_reward:
                print(f"Crystal collected! Score: {game.score}")
            
            # Reset if game over
            if gameOver:
                print(f"Game Over! Final Score: {game.score}")
                print("Press any key to restart...")
                waiting = True
                while waiting:
                    for event in pygame.event.get():
                        if event.type == KEYDOWN or event.type == QUIT:
                            waiting = False
                            if event.type == QUIT:
                                running = False
                game.resetGame()
        
        except Exception as e:
            print(f"Error: {e}")
            break
        
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    main()