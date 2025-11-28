from random import sample
import numpy as np
import tensorflow as tf
from brain import Brain
import keras
import numpy
keras.utils.disable_interactive_logging()

class Dqn():
    def __init__(self, hidden_nodes, lr, maxMemory, discount):
        self.maxMemory = maxMemory
        self.discount = discount
        self.memory = list()

        self.model = Brain(hidden_nodes, 5, 2, lr).model
        self.target_dqn = Brain(hidden_nodes, 5, 2, lr).model
        self.loss_fn = keras.losses.MeanSquaredError()
        self.optimizer = keras.optimizers.AdamW(learning_rate=lr, amsgrad=True)
        self.update_target_dqn()

    def getBatch(self, batchSize, ddqn=False):
        if len(self.memory) < batchSize:
            return None, None

        indices = np.random.randint(0, len(self.memory), size=batchSize)

        #converting data into tensors
        inputs = tf.convert_to_tensor([tf.squeeze(self.memory[idx][0][0]) for idx in indices], dtype=tf.float32)
        actions = tf.convert_to_tensor([self.memory[idx][0][1] for idx in indices], dtype=tf.int32)
        rewards = tf.convert_to_tensor([self.memory[idx][0][2] for idx in indices], dtype=tf.float32)
        nextStates = tf.convert_to_tensor([tf.squeeze(self.memory[idx][0][3]) for idx in indices], dtype=tf.float32)
        gameOvers = tf.convert_to_tensor([self.memory[idx][1] for idx in indices], dtype=tf.float32)


        # Batch predictions for inputs and nextStates
        currentQValues = self.model(inputs, training=False)
        nextQValues = self.model(nextStates, training=False)

        #if it's a DDQN model, use the best action according to the revised Bellman equation
        if ddqn:
            bestActions = tf.argmax(nextQValues, axis=1, output_type=tf.int32)
            nextQTargetValues = self.target_dqn(nextStates, training=False)
            targetQValues = rewards + (1 - gameOvers) * self.discount * tf.gather_nd(
                nextQTargetValues, tf.stack([tf.cast(tf.range(batchSize), dtype=tf.int32), bestActions], axis=1)
            )
        
        else:
            targetQValues = rewards + (1 - gameOvers) * self.discount * tf.reduce_max(nextQValues, axis=1)
        targets = tf.identity(currentQValues)
        indices = tf.stack([tf.range(batchSize, dtype=tf.int32), actions], axis=1)
        targets = tf.tensor_scatter_nd_update(targets, indices, targetQValues)

        return inputs, targets

    @tf.function
    def train_batch(self, inputs, targets):
        with tf.GradientTape() as tape:
            predictions = self.model(inputs, training=True)
            loss = self.loss_fn(targets, predictions)
        gradients = tape.gradient(loss, self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(gradients, self.model.trainable_variables))

    #remove the oldest memory when it is full
    def remember(self, transition, gameOver):
        self.memory.append([transition, gameOver])
        if len(self.memory) > self.maxMemory:
            self.memory.pop(0)

    #doing hard update
    def update_target_dqn(self):
        self.target_dqn.set_weights(self.model.get_weights())

    #soft updating target network's weights
    def soft_update_target_dqn(self, tau: float):
        main_network_weights = self.model.get_weights()
        target_network_weights = self.target_dqn.get_weights()

        new_weights = []
        for target_weight, main_weight in zip(target_network_weights, main_network_weights):
            updated_weight = tau * main_weight + (1 - tau) * target_weight
            new_weights.append(updated_weight)

        #updating target network's weights
        self.target_dqn.set_weights(new_weights)


    def save_weights(self, fname):
        self.model.save_weights(fname)


    def load_weights(self, fname):
        self.model.load_weights(fname)