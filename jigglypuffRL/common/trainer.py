import os

import gym
import torch
import random
import numpy as np

from jigglypuffRL import (
    TD3, 
    PPO1,
    Logger, 
    OrnsteinUhlenbeckActionNoise, 
    DDPG,
    set_seeds,
)

class Trainer():
    def __init__(self, agent, env, logger, buffer=None, off_policy=False, save_interval=0,
                 render=False, max_ep_len=1000, distributed=False, ckpt_log_name='experiment',
                 steps_per_epoch=4000, epochs=10, device='cpu', log_interval=10, batch_size=50,
                 seed=None):
        self.agent = agent
        self.env = env
        self.logger = logger
        self.off_policy = off_policy
        if self.off_policy and buffer==None:
            if self.agent.replay_buffer is None:
                raise Exception("Off Policy Training requires a Replay Buffer")
            else:
                self.buffer = self.agent.replay_buffer
        self.save_interval = save_interval
        self.render = render
        self.max_ep_len = max_ep_len
        self.ckpt_log_name = ckpt_log_name
        self.steps_per_epoch = steps_per_epoch
        self.epochs = epochs
        self.device = device
        self.log_interval = log_interval
        self.batch_size = batch_size
        if seed is not None:
            set_seeds(seed, self.env)

    def train(self):
        raise NotImplementedError

    def save(self):
        saving_params = self.agent.get_hyperparams()
        logdir = self.logger.logdir
        algo = self.agent.__class__.__name__
        env_name = self.env.envs[0].unwrapped.spec.id

        save_dir = '{}/checkpoints/{}_{}'.format(logdir, algo, env_name)
        os.makedirs(save_dir, exist_ok=True)
        torch.save('{}/{}.pt'.format(save_dir, self.ckpt_log_name))

    @property
    def n_envs(self):
        return self.env.n_envs


class OffPolicyTrainer(Trainer):
    def __init__(self, agent, env, logger, buffer=None, off_policy=True, save_interval=0,
                 render=False, max_ep_len=1000, distributed=False, ckpt_log_name='experiment',
                 steps_per_epoch=4000, epochs=10, device='cpu', log_interval=10, batch_size=50,
                 warmup_steps=1000, start_update=1000, update_interval=50, seed=0):
        super(OffPolicyTrainer, self).__init__(agent, env, logger, buffer, 
                                               off_policy, save_interval, render, max_ep_len,
                                               distributed, ckpt_log_name,steps_per_epoch, 
                                               epochs, device, log_interval, batch_size, seed
                                               )
        self.warmup_steps = warmup_steps
        self.update_interval = update_interval
        self.start_update = start_update
        
    def train(self):
        state, episode_reward, episode_len, episode = self.env.reset(), 0, 0, 0
        total_steps = self.steps_per_epoch * self.epochs

        if self.agent.noise is not None:
            self.agent.noise.reset()

        for t in range(total_steps):

            if t < self.warmup_steps:
                action = self.env.action_space.sample()
            else:
                action = self.agent.select_action(state, deterministic=True)

            next_state, reward, done, info = self.env.step(action)
            if self.render:
                self.env.render()

            episode_reward += reward
            episode_len += 1
            
            done = False if episode_len == self.max_ep_len else done

            self.buffer.push((state, action, reward, next_state, done))

            states = next_state

            if done or (episode_len == self.max_ep_len):
                if self.agent.noise is not None:
                    self.agent.noise.reset()

                if episode % self.log_interval == 0:
                    logger.write({'timestep':t,'Episode':episode,
                                  'Episode Reward':episode_reward})

                state, episode_reward, episode_len = self.env.reset(), 0, 0
                episode += 1

            # update params
            if t >= self.start_update and t % self.update_interval == 0:
                for _ in range(self.update_interval):
                    batch = self.buffer.sample(self.batch_size)
                    states, actions, next_states, rewards, dones = (
                        x.to(self.device) for x in batch
                    )
                    if self.agent.__class__.__name__ == "TD3":
                        self.agent.update_params(
                            states, actions, next_states, rewards, dones, t
                        )
                    else:
                        self.agent.update_params(
                            states, actions, next_states, rewards, dones
                        )


            if t >= self.start_update and self.save_interval!=0 and t % self.save_interval == 0:
                self.checkpoint = self.agent.get_hyperparams()
                self.save()

        self.env.close()
        self.logger.close()   


class OnPolicyTrainer(Trainer):
    def __init__(self, agent, env, logger, save_interval=0, render=False, 
                 max_ep_len=1000, distributed=False, ckpt_log_name='experiment', 
                 steps_per_epoch=4000, epochs=10, device='cpu', log_interval=10, 
                 batch_size=50, seed=None):
        super().__init__(agent, env, logger, buffer=None, off_policy=False, 
                         save_interval=save_interval, render=render, max_ep_len=max_ep_len, 
                         distributed=distributed, ckpt_log_name=ckpt_log_name, 
                         steps_per_epoch=steps_per_epoch, epochs=epochs, device=device, 
                         log_interval=log_interval, batch_size=batch_size, seed=seed)

    def train(self):
       for episode in range(self.epochs):

            epoch_reward = 0

            for i in range(self.agent.actor_batch_size):

                state = self.env.reset()
                done = False

                for t in range(self.agent.timesteps_per_actorbatch):
                    action = self.agent.select_action(state)
                    state, reward, done, _ = self.env.step(np.array(action))

                    if self.render:
                        self.env.render()

                    self.agent.policy_old.traj_reward.append(reward)

                    if done:
                        break

                epoch_reward += (
                    np.sum(self.agent.policy_old.traj_reward) / self.agent.actor_batch_size
                )
                self.agent.get_traj_loss()

            self.agent.update_policy(episode)

            if episode % self.log_interval == 0:
                logger.write({'Episode':episode, 'Reward':epoch_reward, 'Timestep':i*episode*self.agent.timesteps_per_actorbatch})

            if episode % self.agent.policy_copy_interval == 0:
                self.agent.policy_old.load_state_dict(self.agent.policy_new.state_dict())

            if self.save_interval!=0 and episode % self.save_interval == 0:
                self.checkpoint = self.agent.get_hyperparams()
                self.save()

            self.env.close()
            self.logger.close()
                     

if __name__ == "__main__":
    log_dir = os.getcwd()
    logger = Logger(log_dir, ['stdout'])
    env = gym.make("CartPole-v0")
    # algo = TD3("mlp", env, noise=OrnsteinUhlenbeckActionNoise, seed=0)

    # trainer = OffPolicyTrainer(algo, env, logger, render=True, seed=0)
    # trainer.train()
    algo = PPO1("mlp", env, seed=0)
    trainer = OnPolicyTrainer(algo, env, logger, render=True, seed=0, epochs=100, log_interval=1)
    trainer.train()
                
