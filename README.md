# JigglypuffRL
[![pypi](https://img.shields.io/badge/pypi-jigglypuff--rl-blue)](https://pypi.org/project/jigglypuff-rl/)
[![GitHub license](https://img.shields.io/github/license/SforAiDl/JigglypuffRL)](https://github.com/SforAiDl/JigglypuffRL/blob/master/LICENSE)
[![Build Status](https://travis-ci.com/SforAiDl/JigglypuffRL.svg?branch=master)](https://travis-ci.com/SforAiDl/JigglypuffRL)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/SforAiDl/JigglypuffRL.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/SforAiDl/JigglypuffRL/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/SforAiDl/JigglypuffRL.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/SforAiDl/JigglypuffRL/context:python)

## Installation

We suggest creating a conda virtual environment before installing our package.
```
conda create -n JgRL_env python=3.6 pip
conda activate JgRL_env
```

### From Source (Recommended)
```
git clone https://github.com/SforAiDl/JigglypuffRL.git
cd JigglypuffRL
pip install -r requirements.txt
python setup.py install
```

### Using Pip
```
pip install jigglypuff-rl # for most recent stable release
pip install jigglypuff-rl==0.0.1dev2 # for most recent development release
```

## Usage
```python
from jigglypuffRL import PPO1
import gym

env = gym.make('CartPole-v0')
agent = PPO1('MlpPolicy', 'MlpValue', env, epochs=500, tensorboard_log='./runs/')

agent.learn()
```
