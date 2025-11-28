from flappybirdenv.flappybird import FlappyBird
from dqn import Dqn
import numpy as np
import keras
import yaml
from datetime import datetime

keras.utils.disable_interactive_logging()


class Agent:
    def __init__(self):
        #loading the hyperparameters
        with open("hyperparameters.yml", "r") as f:
            params = yaml.safe_load(f)

        self.learningRate = params["learningRate"]
        self.maxMemory = params["maxMemory"]
        self.gamma = params["gamma"]
        self.batchSize = params["batchSize"]
        self.epsilon = params["epsilon"]
        self.epsilonDecayRate = params["epsilonDecayRate"]
        self.epsilonMin = params["epsilonMin"]
        self.hidden_nodes = params["hidden_nodes"]
        self.ddqn_enable = params["ddqn_enable"]
        self.tau = params["tau"]
        self.training = params["train"]

        #initializing dqn
        self.DQN = Dqn(hidden_nodes=self.hidden_nodes, lr=self.learningRate,
                       maxMemory=self.maxMemory, discount=self.gamma)
        self.weights_file_name = "dqntrain.weights.h5"
        if not self.training:
            self.DQN.load_weights(self.weights_file_name)

        #setting the default parameters of the game and rewards
        self.game_config = { "pipe_prob": 0.9,"pipe_spacing": 150, "num_portals": 1, "crystal_prob": 0.2, "max_steps_per_epoch": 500}

        self.reward_config = {"pass_pipe": 100.0,"crystal": 75.0, "portal": 50.0, "death": -10.0, "survival": 1.0}


        self.epoch = 0
        self.currentState = np.zeros((1, 5))
        self.nextState = np.zeros((1, 5))
        self.totReward = 0

        self.log_file = f"./logs/log{datetime.now().strftime('%m-%d--%H-%M')}.txt"
        self.log_parameters()

        #to ask user's input
        self.get_user_config()

        self.env = FlappyBird()
        self.env.update_config(
            pipe_prob=self.game_config["pipe_prob"],
            pipe_spacing=self.game_config["pipe_spacing"], num_portals=self.game_config["num_portals"],
            crystal_prob=self.game_config["crystal_prob"], max_steps=self.game_config["max_steps_per_epoch"])



    def log_default(self, epoch, totReward, epsilon, score):
        with open(self.log_file, "a") as log:
            log.write(f"{datetime.now()}: epoch: {epoch} | totalReward = {totReward} "
                      f"| epsilon = {epsilon:.3f} | pipes passed = {score}\n")

    #to store the logs of rewards, epsilon and other important things
    def log_parameters(self):
        with open("hyperparameters.yml", "r") as f:
            params = yaml.safe_load(f)
        with open(self.log_file, "a") as log:
            log.write("Hyperparameters:\n")
            for k, v in params.items():
                log.write(f"{k}: {v}\n")
            log.write("\nGame Config:\n")
            for k, v in self.game_config.items():
                log.write(f"{k}: {v}\n")
            log.write("\nReward Config:\n")
            for k, v in self.reward_config.items():
                log.write(f"{k}: {v}\n")
            log.write("\n")

    #to get the user's input for some parameters.
    def get_user_config(self):
        print("Customize Game Parameters")
        for key in self.game_config:
            current_value = self.game_config[key]
            try:
                user_input = input(f"{key} (current={current_value}): ")
                if user_input.strip() != "":
                    if isinstance(current_value, int):
                        self.game_config[key] = int(user_input)
                    elif isinstance(current_value, float):
                        self.game_config[key] = float(user_input)
            except ValueError:
                print(f"Invalid input for {key}, keeping current value {current_value}.")

        print("Customize Rewards")
        for key in self.reward_config:
            current_value = self.reward_config[key]
            try:
                user_input = input(f"{key} reward (current={current_value}): ")
                if user_input.strip() != "":
                    self.reward_config[key] = float(user_input)
            except ValueError:
                print(f"Invalid input for {key}, keeping current value {current_value}.")

    #training the flappy
    def train(self, max_epochs=100):
        while self.epoch < max_epochs:
            self.epoch += 1
            self.env.resetGame()
            self.currentState[0] = self.env.getGameState()
            gotReward = False
            pipes_passed = 0
            gameOver = False
            step_count = 0

            print(f"\nEpoch {self.epoch} starting...")

            while not gameOver and step_count < self.game_config["max_steps_per_epoch"]:
                step_count += 1
                #epsilon for e-greedy algorithm
                if np.random.rand() <= self.epsilon and self.training:
                    action = 1 if np.random.rand() < 0.2 else 0
                else:
                    qvalues = self.DQN.model(self.currentState)[0]
                    action = np.argmax(qvalues)

                gameOver, gotReward, portal_reward, crystal_reward = self.env.step(action, self.epoch)
                self.nextState[0] = self.env.getGameState()

                #defining rewards
                if gotReward:
                    reward_this_round = self.reward_config["pass_pipe"] #reward for going through pipe gap successfully
                    pipes_passed += 1
                elif crystal_reward:
                    reward_this_round = self.reward_config["crystal"] #for collecting crystals
                elif portal_reward:
                    reward_this_round = self.reward_config["portal"] #for passing through portal
                elif gameOver:
                    reward_this_round = self.reward_config["death"]  #for when you die
                else:
                    reward_this_round = self.reward_config["survival"]     #for staying alive

                #calling the memory function to remember experience
                if self.training:
                    if gotReward or crystal_reward or portal_reward:
                        for _ in range(3):
                            self.DQN.remember([np.copy(self.currentState), action, reward_this_round, np.copy(self.nextState)], gameOver)
                    else:
                        self.DQN.remember([np.copy(self.currentState), action, reward_this_round, np.copy(self.nextState)], gameOver)

                self.currentState = np.copy(self.nextState)
                self.totReward += reward_this_round

            self.log_default(self.epoch, self.totReward, self.epsilon, pipes_passed)
            print(f"Epoch {self.epoch} finished: Total Reward = {self.totReward:.1f}, Pipes = {pipes_passed}, Epsilon = {self.epsilon:.3f}")

            #training the DQN every 2 epochs
            if self.training and self.epoch % 2 == 0:
                inputs, targets = self.DQN.getBatch(self.batchSize, True)
                if inputs is not None and targets is not None:
                    self.DQN.train_batch(inputs, targets)
                if self.epoch % 100 == 0:
                    self.DQN.save_weights(self.weights_file_name)
                if self.ddqn_enable:
                    self.DQN.soft_update_target_dqn(self.tau)
                self.epsilon = max(self.epsilon * self.epsilonDecayRate, self.epsilonMin)
                self.totReward = 0


if __name__ == "__main__":
    agent = Agent()
    agent.train(max_epochs=50)
