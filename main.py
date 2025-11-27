from flappybirdenv.flappybird import FlappyBird
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

            # Game loop until game is not over
            gameOver = False
            while not gameOver:
                # Taking an action using the epsilon greedy policy
                action = None
                if np.random.rand() <= self.epsilon and self.training:
                    # Bias toward not jumping (80% no jump, 20% jump) for better exploration
                    action = 1 if np.random.rand() < 0.2 else 0
                else:
                    qvalues = self.DQN.model(self.currentState)[0]
                    action = np.argmax(qvalues)

                # Take the action and get the game state.
                gameOver, gotReward, portal_reward, crystal_reward = self.env.step(action, self.epoch)
                self.nextState[0] = self.env.getGameState()

                # rewards:
                if gotReward:
                    reward_this_round = 100.  # High reward for passing pipes
                    pipes_passed += 1
                elif crystal_reward:
                    reward_this_round = 75.   # High reward for risky crystal collection
                    pipes_passed += 1
                elif portal_reward:
                    reward_this_round = 50.   # Reward for entering dangerous portal
                elif gameOver:
                    if hasattr(self.env, 'portal_mode') and self.env.portal_mode:
                        reward_this_round = -10.  # Much less penalty for spike death
                    else:
                        reward_this_round = -10.  # Reduced penalty for normal death
                else:
                    if hasattr(self.env, 'portal_mode') and self.env.portal_mode:
                        reward_this_round = 0.5   # Higher survival in portal
                    else:
                        reward_this_round = 1.0   # Higher survival reward

                # Remember new experience with prioritization
                if self.training:
                    # Store successful experiences multiple times to prevent forgetting
                    if gotReward or crystal_reward or portal_reward:
                        for _ in range(3):  # Store 3 times for important experiences
                            self.DQN.remember([np.copy(self.currentState), action, reward_this_round, np.copy(self.nextState)], gameOver)
                    else:
                        self.DQN.remember([np.copy(self.currentState), action, reward_this_round, np.copy(self.nextState)], gameOver)

                self.currentState = np.copy(self.nextState)
                self.totReward += reward_this_round

            # Log the current epoch's information
            self.log_default(self.epoch, self.totReward, self.epsilon, pipes_passed)
            
            # Debug: Print first few epochs
            if self.epoch <= 5:
                print(f"Epoch {self.epoch}: Total Reward = {self.totReward:.1f}, Pipes = {pipes_passed}, Epsilon = {self.epsilon:.3f}")

            # Train less frequently to prevent catastrophic forgetting
            if self.training and self.epoch % 2 == 0:  # Train every 2nd epoch
                inputs, targets = self.DQN.getBatch(self.batchSize, True)
                if inputs is not None and targets is not None:
                    self.DQN.train_batch(inputs, targets)

                # Save the weights after 100 epochs
                if self.epoch % 100 == 0:
                    self.DQN.save_weights(self.weights_file_name)

                # If it's a DDQN model, update the target network weights using the soft update.
                # Can be updated using the hard update in update_target_dqn() function in dqn.py for experimentation.
                if self.ddqn_enable:
                    self.DQN.soft_update_target_dqn(self.tau)

                # decrease epsilon and reset the total reward for this epoch
                self.epsilon = max(self.epsilon * self.epsilonDecayRate, self.epsilonMin)
                self.totReward = 0


if __name__ == "__main__":
    agent = Agent()
    agent.train()