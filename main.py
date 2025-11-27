from flappybirdenv.flappybird import FlappyBird
from flappybirdenv.flappybird_constants import SCREEN_HEIGHT
from dqn import Dqn
import numpy as np
import keras
import yaml
from datetime import datetime
keras.utils.disable_interactive_logging()


class Agent():
    def __init__(self):
        parameters = None
        with open("hyperparameters.yml", "r") as parameters_file:
            parameters = yaml.safe_load(parameters_file)

        self.learningRate = parameters["learningRate"]
        self.maxMemory = parameters["maxMemory"]
        self.gamma = parameters["gamma"]
        self.batchSize = parameters["batchSize"]
        self.epsilon = parameters["epsilon"]
        self.epsilonDecayRate = parameters["epsilonDecayRate"]
        self.epsilonMin = parameters["epsilonMin"]
        self.hidden_nodes = parameters["hidden_nodes"]
        self.ddqn_enable = parameters["ddqn_enable"]
        self.tau = parameters["tau"]
        self.training = parameters["train"]

        # Initialize environment, and the experience replay memory
        self.DQN = Dqn(hidden_nodes=self.hidden_nodes, lr=self.learningRate, maxMemory=self.maxMemory, discount=self.gamma)
        self.weights_file_name = "dqntrain.weights.h5"
        if not self.training:
            self.DQN.load_weights(self.weights_file_name)

        # main variables
        self.epoch = 0
        self.currentState = np.zeros((1, 5))
        self.nextState = np.zeros((1, 5))
        self.totReward = 0
        self.recent_scores = []
        self.best_score = 0

        # Create a new log file and log the parameters
        self.log_file = f"./logs/log{datetime.now().strftime('%m-%d--%H-%M')}.txt"

        self.log_parameters()

        # Create game environment
        self.env = FlappyBird()


    def log_default(self, epoch, totReward, epsilon, score, mode="+a"):
        with open(self.log_file, mode) as log:
            log.write(
                f"{datetime.now()}: epoch: {epoch} | totalReward = {totReward} | epsilon = {epsilon} | pipes passed = {score}\n")

    def log_parameters(self, mode="a"):
        with open("hyperparameters.yml", "r") as parameters_file:
            parameters = yaml.safe_load(parameters_file)

        with open(self.log_file, mode) as f:
            for key, value in parameters.items():
                f.write(f"{key}: {value}\n")

            f.write("\n")

    def train(self):
        while self.epoch < 50000:
            self.epoch += 1

            # get current game state:
            self.env.resetGame()
            self.currentState[0] = self.env.getGameState()
            gotReward = False
            self.topCollision = False
            pipes_passed = 0
            total_pipes_this_episode = 0

            # Game loop until game is not over
            gameOver = False
            while not gameOver:
                # Taking an action using the epsilon greedy policy
                # if random number is less than epsilon, take a random action, otherwise,
                # let the model predict an action and take the action with the highest Q-value
                action = None
                if np.random.rand() <= self.epsilon and self.training:
                    # Random exploration: 50% chance to jump, 50% chance to do nothing
                    # This provides better exploration than the previous approach
                    action = np.random.randint(0, 2)
                else:
                    qvalues = self.DQN.model(self.currentState)[0]
                    action = np.argmax(qvalues)

                # Take the action and get the game state.
                gameOver, gotReward, portal_reward = self.env.step(action, self.epoch)
                self.nextState[0] = self.env.getGameState()

                # rewards:
                if gotReward:
                    reward_this_round = 10.  # Higher reward for passing pipes
                    total_pipes_this_episode += 1
                elif portal_reward:
                    reward_this_round = 5.   # Reward for entering portals
                elif gameOver:
                    reward_this_round = -10. # Higher penalty for dying
                else:
                    # Base survival reward
                    reward_this_round = 0.5
                    
                    # Bonus reward for being near the pipe gap center (helps guide learning)
                    state = self.env.getGameState()
                    if len(state) >= 3:
                        obstacle_top_y = state[0] * SCREEN_HEIGHT
                        obstacle_bottom_y = state[1] * SCREEN_HEIGHT
                        bird_y = state[3] * SCREEN_HEIGHT
                        gap_center = (obstacle_top_y + obstacle_bottom_y) / 2
                        distance_to_gap_center = abs(bird_y - gap_center)
                        
                        # Small bonus if bird is close to gap center (within 50 pixels)
                        if distance_to_gap_center < 50:
                            reward_this_round += 0.2

                # Remeber new experience
                if self.training:
                    self.DQN.remember([np.copy(self.currentState), action, reward_this_round, np.copy(self.nextState)], gameOver)

                self.currentState = np.copy(self.nextState)
                self.totReward += reward_this_round

            # Log the current epoch's information
            self.log_default(self.epoch, self.totReward, self.epsilon, total_pipes_this_episode)

            # Train the model on the current state and the expected values of the action taken (Q values). Get these
            # vlaues from the getBatch() function then feed it into the model for training.
            if self.training:
                inputs, targets = self.DQN.getBatch(self.batchSize, True)
                if inputs is not None and targets is not None:
                    # self.DQN.model.train_on_batch(inputs, targets)
                    self.DQN.train_batch(inputs, targets)

                # Save the weights after 100 epochs
                if self.epoch % 100 == 0:
                    self.DQN.save_weights(self.weights_file_name)

                # If it's a DDQN model, update the target network weights using the soft update.
                # Can be updated using the hard update in update_target_dqn() function in dqn.py for experimentation.
                if self.ddqn_enable:
                    self.DQN.soft_update_target_dqn(self.tau)

                # Track performance and reset epsilon if needed
                self.recent_scores.append(total_pipes_this_episode)
                if len(self.recent_scores) > 100:
                    self.recent_scores.pop(0)
                
                if total_pipes_this_episode > self.best_score:
                    self.best_score = total_pipes_this_episode
                
                # Reset epsilon if performance is consistently poor
                if len(self.recent_scores) >= 50 and max(self.recent_scores[-50:]) == 0 and self.epsilon < 0.4:
                    self.epsilon = 0.5
                    self.recent_scores = []  # Clear history to prevent immediate retrigger
                    print(f"Resetting epsilon to {self.epsilon} due to poor performance at epoch {self.epoch}")
                elif len(self.recent_scores) >= 20 and max(self.recent_scores[-20:]) == 0 and self.epsilon <= 0.1:
                    self.epsilon = 0.3
                    self.recent_scores = []  # Clear history
                    print(f"Early epsilon reset to {self.epsilon} at epoch {self.epoch}")
                
                # decrease epsilon and reset the total reward for this epoch
                self.epsilon = max(self.epsilon * self.epsilonDecayRate, self.epsilonMin)
                self.totReward = 0


if __name__ == "__main__":
    agent = Agent()
    agent.train()