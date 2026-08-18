from umlsl_sim.rl.gym_env.umlsl_env import MlslEnv
from umlsl_sim.rl.rewards.reward_types import RewardType
from umlsl_sim.rl.rewards.reward_registry import register_reward_model

@register_reward_model(RewardType.INITIAL_REWARD)
class InitialReward(MlslEnv):
    def compute_reward(self):
        if self.game_model.agent_car.score > self.agent_score:
            self.agent_score = self.game_model.agent_car.score
            return 1
        elif self.game_model.agent_car.illegal_move:
            self.game_model.agent_car.illegal_move = False
            return -1
        elif self.result == "deadlock":
            return -5
        elif self.game_model.agent_car.get_death_status():
            return -10
        else:
            return 0