from flappybirdenv.flappybird import FlappyBird
from dqn import Dqn
import numpy as np
import keras
import yaml
from datetime import datetime
import pygame
import time
keras.utils.disable_interactive_logging()

class EducationalRLAgent:
    def __init__(self):
        # Get user preferences
        self.get_user_settings()
        
        # Initialize DQN with user settings
        self.DQN = Dqn(hidden_nodes=self.hidden_nodes, lr=self.learningRate, 
                      maxMemory=self.maxMemory, discount=self.gamma)
        
        # Training variables
        self.epoch = 0
        self.currentState = np.zeros((1, 5))
        self.nextState = np.zeros((1, 5))
        self.totReward = 0
        self.episode_rewards = []
        self.pipes_passed_history = []
        
        # Create game environment
        self.env = FlappyBird(portal_count=self.portal_count)
        
        print(f"\n🎮 Educational RL Training Started!")
        print(f"📊 Watch how your settings affect learning...")
        
    def get_user_settings(self):
        print("🎓 Welcome to Educational Reinforcement Learning!")
        print("Configure your AI agent and see how parameters affect learning:\n")
        
        # Game settings
        self.portal_count = int(input("🚪 Number of portal pipes (1-5): "))
        self.portal_count = max(1, min(5, self.portal_count))
        
        self.max_episodes = int(input("📈 Number of training episodes (50-500): "))
        self.max_episodes = max(50, min(500, self.max_episodes))
        
        # RL Hyperparameters with explanations
        print("\n🧠 RL Hyperparameters:")
        print("Gamma (discount factor): How much future rewards matter (0.9-0.99)")
        self.gamma = float(input("γ (gamma): "))
        self.gamma = max(0.9, min(0.99, self.gamma))
        
        print("Learning rate: How fast the AI learns (0.0001-0.01)")
        self.learningRate = float(input("α (learning rate): "))
        self.learningRate = max(0.0001, min(0.01, self.learningRate))
        
        print("Epsilon: Exploration vs exploitation (0.7-0.95)")
        self.epsilon = float(input("ε (epsilon): "))
        self.epsilon = max(0.7, min(0.95, self.epsilon))
        
        # Reward structure
        print("\n🎯 Reward Structure:")
        self.pipe_reward = float(input("Pipe passing reward (50-200): "))
        self.crystal_reward = float(input("Crystal collection reward (30-100): "))
        self.death_penalty = float(input("Death penalty (5-50): "))
        
        # Fixed parameters
        self.epsilonDecayRate = 0.995
        self.epsilonMin = 0.1
        self.maxMemory = 20000
        self.batchSize = 32
        self.hidden_nodes = 64
        
        print(f"\n✅ Configuration Complete!")
        print(f"🎯 Training for {self.max_episodes} episodes with {self.portal_count} portals")
        
    def display_stats(self):
        """Display real-time learning statistics"""
        if self.epoch % 10 == 0 and self.epoch > 0:
            avg_reward = np.mean(self.episode_rewards[-10:]) if self.episode_rewards else 0
            avg_pipes = np.mean(self.pipes_passed_history[-10:]) if self.pipes_passed_history else 0
            
            print(f"\n📊 Episode {self.epoch}/{self.max_episodes}")
            print(f"   🏆 Avg Reward (last 10): {avg_reward:.1f}")
            print(f"   🚀 Avg Pipes Passed: {avg_pipes:.1f}")
            print(f"   🎲 Exploration Rate: {self.epsilon:.3f}")
            print(f"   🧠 Memory Size: {len(self.DQN.memory)}")
            
            # Learning insights
            if avg_pipes > 2:
                print("   💡 AI is learning to navigate pipes!")
            elif avg_pipes > 0.5:
                print("   📈 AI showing improvement...")
            else:
                print("   🔄 AI still exploring...")
    
    def train(self):
        while self.epoch < self.max_episodes:
            self.epoch += 1
            
            # Reset game
            self.env.resetGame()
            self.currentState[0] = self.env.getGameState()
            pipes_passed = 0
            episode_reward = 0
            
            # Game loop
            gameOver = False
            while not gameOver:
                # Action selection
                if np.random.rand() <= self.epsilon:
                    action = 1 if np.random.rand() < 0.2 else 0  # Biased exploration
                else:
                    qvalues = self.DQN.model(self.currentState)[0]
                    action = np.argmax(qvalues)
                
                # Take action
                gameOver, gotReward, portal_reward, crystal_reward = self.env.step(action, self.epoch)
                self.nextState[0] = self.env.getGameState()
                
                # Calculate rewards with user settings
                if gotReward:
                    reward = self.pipe_reward
                    pipes_passed += 1
                elif crystal_reward:
                    reward = self.crystal_reward
                elif portal_reward:
                    reward = 25.0
                elif gameOver:
                    reward = -self.death_penalty
                else:
                    reward = 1.0  # Survival reward
                
                # Store experience
                self.DQN.remember([np.copy(self.currentState), action, reward, 
                                 np.copy(self.nextState)], gameOver)
                
                self.currentState = np.copy(self.nextState)
                episode_reward += reward
            
            # Store episode stats
            self.episode_rewards.append(episode_reward)
            self.pipes_passed_history.append(pipes_passed)
            
            # Train every 2 episodes
            if self.epoch % 2 == 0:
                inputs, targets = self.DQN.getBatch(self.batchSize, True)
                if inputs is not None and targets is not None:
                    self.DQN.train_batch(inputs, targets)
            
            # Update epsilon
            self.epsilon = max(self.epsilon * self.epsilonDecayRate, self.epsilonMin)
            
            # Display progress
            self.display_stats()
            
            # Show final results
            if self.epoch == self.max_episodes:
                self.show_final_results()
    
    def show_final_results(self):
        """Display final learning analysis"""
        print(f"\n🎓 Training Complete! Final Analysis:")
        print(f"=" * 50)
        
        final_avg_reward = np.mean(self.episode_rewards[-20:])
        final_avg_pipes = np.mean(self.pipes_passed_history[-20:])
        best_episode = max(self.pipes_passed_history)
        
        print(f"🏆 Final Performance:")
        print(f"   Average Reward: {final_avg_reward:.1f}")
        print(f"   Average Pipes Passed: {final_avg_pipes:.1f}")
        print(f"   Best Episode: {best_episode} pipes")
        
        print(f"\n🧠 Your Parameter Effects:")
        print(f"   Gamma ({self.gamma}): {'High future focus' if self.gamma > 0.95 else 'Balanced focus'}")
        print(f"   Learning Rate ({self.learningRate}): {'Fast learning' if self.learningRate > 0.005 else 'Stable learning'}")
        print(f"   Pipe Reward ({self.pipe_reward}): {'High motivation' if self.pipe_reward > 100 else 'Moderate motivation'}")
        
        # Learning insights
        if final_avg_pipes > 3:
            print(f"\n🌟 Excellent! Your AI learned to consistently pass pipes!")
        elif final_avg_pipes > 1:
            print(f"\n👍 Good progress! AI is learning the basics.")
        else:
            print(f"\n🔧 Try adjusting: Higher rewards, lower death penalty, or more episodes.")
        
        print(f"\n💡 Experiment with different parameters to see how they affect learning!")

if __name__ == "__main__":
    agent = EducationalRLAgent()
    agent.train()