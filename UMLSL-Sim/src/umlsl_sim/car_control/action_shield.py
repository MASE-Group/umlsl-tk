"""Safety shield: turns the SafetyController's verdict into an action mask.

This is the *masking* alternative to the safety-aware reward profile. Both read
the same oracle -- :class:`SafetyController` -- but they use it differently:

* ``SafetyAwareReward`` lets the agent take any action and adds a penalty term
  afterwards, so unsafe actions stay reachable and the reward has to trade
  safety off against progress.
* ``ActionShield`` removes unsafe actions from the agent's choice set before it
  acts, so the reward is free to speak only about the objective.

The two are independent: a shielded run may use any reward profile, including
the safety-aware one (the shield and the reward then keep separate
SafetyController instances, which is harmless -- see *Side effects* below).

## Mask layout

``MlslEnv`` uses ``spaces.MultiDiscrete([MAX_ACC + MAX_DEC + 1, 3])`` and
sb3-contrib expects the per-dimension masks concatenated, so the returned array
has ``MAX_ACC + MAX_DEC + 1 + 3`` entries:

* indices ``0 .. MAX_ACC + MAX_DEC`` -- acceleration ``index - MAX_DEC``
* the last three -- lane change ``[-1 (right), 0 (stay), +1 (left)]``

## Soundness of per-dimension masking

Per-dimension masks cannot express a joint constraint, and
``get_safe_lane_change`` does depend on the acceleration -- but only through the
feasibility test ``remaining_space < (speed + acc) * LANECHANGE_TIME_STEPS``,
which is monotone: the larger the acceleration, the harder it is to satisfy.
The masks are therefore built by evaluating the lane-change verdict at the
*largest* acceleration the acceleration mask admits. Every acceleration the mask
allows is then at most that one, so any (acceleration, lane change) pair the
mask permits is one the safety controller accepts. The mask is conservative,
never permissive.

Deceleration needs no separate argument: ``get_accelerate`` scans candidate
accelerations downwards and returns the largest safe one, and every safety test
it applies (rear-end overlap, crossing time-of-arrival versus other cars'
time-to-leave, intersection priority) is monotone in speed. Anything at or below
the returned maximum is therefore also safe.

## Side effects

``SafetyController.get_max_acceleration`` may yield the car's intersection
priority to break a deadlock. Querying the shield every step is what makes that
happen for the agent car, exactly as it already happens for NPCs through their
controllers and for the agent under the safety-aware reward.
"""

from typing import TYPE_CHECKING

import numpy as np

from umlsl_sim.car_control.safety_controller import SafetyController
from umlsl_sim.constants import MAX_ACC, MAX_DEC

if TYPE_CHECKING:
    from umlsl_sim.simulation.car import Car
    from umlsl_sim.simulation.traffic_environment import TrafficEnv

# Sizes of the two MultiDiscrete components, and of the concatenated mask.
ACC_ACTIONS: int = MAX_ACC + MAX_DEC + 1
LANE_ACTIONS: int = 3
MASK_LENGTH: int = ACC_ACTIONS + LANE_ACTIONS

# Index of maximal braking in the acceleration block, and of "stay in lane" in
# the lane block. These are the fallbacks that keep the mask non-empty.
FULL_BRAKE_INDEX: int = 0
KEEP_LANE_INDEX: int = ACC_ACTIONS + 1


class ActionShield:
    """Builds per-step action masks for the agent car from a SafetyController.

    The shield owns its own SafetyController and rebuilds it whenever the agent
    car is replaced, which ``TrafficEnv.reset()`` does at the start of every
    episode. Callers therefore do not need to reset it explicitly.

    Attributes:
        steps (int): Masks produced since construction.
        forced_brake_steps (int): Steps whose mask admitted maximal braking
            only. ``SafetyController`` returns maximal braking both when it is
            the only safe choice and when none of the accelerations it tried
            passed its checks, so this counts "the shield had nothing better to
            offer" rather than "the shield failed".
        empty_mask_steps (int): Steps where a block came back with no action at
            all and the fallback had to be forced in. Expected to stay 0; a
            non-zero value means an assumption above no longer holds.
        allowed_actions_total (int): Sum over steps of the number of joint
            (acceleration, lane) pairs the mask allowed. Divide by ``steps`` for
            the mean size of the agent's choice set.
    """

    def __init__(self, game_model: "TrafficEnv") -> None:
        """Initialize the shield.

        Args:
            game_model (TrafficEnv): The simulation whose agent car is shielded.
        """
        self.game_model: "TrafficEnv" = game_model

        self._car: "Car | None" = None
        self._controller: SafetyController | None = None

        self.steps: int = 0
        self.forced_brake_steps: int = 0
        self.empty_mask_steps: int = 0
        self.allowed_actions_total: int = 0

    def action_masks(self) -> np.ndarray:
        """Return the concatenated per-dimension mask for the current state.

        Must be called *before* the simulation advances: it describes which
        actions are safe from where the agent stands now.

        Returns:
            np.ndarray: Boolean array of length ``MASK_LENGTH``. All-true when
                there is no live agent car (the episode is over in that case and
                the environment terminates on the same step).
        """
        self.steps += 1
        mask = np.zeros(MASK_LENGTH, dtype=bool)

        agent = self.game_model.agent_car
        if agent is None or agent.get_death_status():
            # Nothing to protect. Masking everything off here would leave the
            # policy with no action to sample on the final step of an episode.
            mask[:] = True
            self._record(mask)
            return mask

        controller = self._controller_for(agent)

        max_acc = int(np.clip(controller.get_max_acceleration(), -MAX_DEC, MAX_ACC))
        mask[: max_acc + MAX_DEC + 1] = True

        # Evaluated at the largest admitted acceleration, so the verdict holds
        # for every acceleration the mask allows (see module docstring).
        reservations = self.game_model.reservation_management.get_car_reservations(agent.id)
        mask[ACC_ACTIONS:] = controller.get_safe_lane_change(reservations, max_acc)

        self._apply_fallbacks(mask)
        self._record(mask)
        return mask

    def stats(self) -> dict[str, float]:
        """Summary of what the shield did, for evaluation and logging.

        Returns:
            dict[str, float]: ``steps``, ``forced_brake_steps``,
                ``empty_mask_steps``, ``mean_allowed_actions`` (mean number of
                joint actions left open) and ``total_actions`` (how many there
                are in all, for scale).
        """
        return {
            "steps": self.steps,
            "forced_brake_steps": self.forced_brake_steps,
            "empty_mask_steps": self.empty_mask_steps,
            "mean_allowed_actions": (self.allowed_actions_total / self.steps) if self.steps else 0.0,
            "total_actions": ACC_ACTIONS * LANE_ACTIONS,
        }

    def reset_stats(self) -> None:
        """Zero the counters without touching the cached controller."""
        self.steps = 0
        self.forced_brake_steps = 0
        self.empty_mask_steps = 0
        self.allowed_actions_total = 0

    def _controller_for(self, agent: "Car") -> SafetyController:
        """Return the SafetyController for `agent`, rebuilding it if the agent
        car object changed (which happens on every ``TrafficEnv.reset()``)."""
        if self._controller is None or self._car is not agent:
            self._car = agent
            self._controller = SafetyController(
                car=agent,
                cars=self.game_model.cars,
                reservation_management=self.game_model.reservation_management,
            )
        return self._controller

    def _apply_fallbacks(self, mask: np.ndarray) -> None:
        """Guarantee both blocks offer at least one action.

        Neither branch is expected to fire: ``get_accelerate`` falls back to
        maximal braking and ``get_safe_lane_change`` always marks "stay" safe.
        They are kept because a masked policy has no defined behaviour on an
        empty mask, and a silent NaN would be a much worse failure than a
        counted fallback.
        """
        if not mask[:ACC_ACTIONS].any():
            mask[FULL_BRAKE_INDEX] = True
            self.empty_mask_steps += 1
        if not mask[ACC_ACTIONS:].any():
            mask[KEEP_LANE_INDEX] = True
            self.empty_mask_steps += 1

        if mask[:ACC_ACTIONS].sum() == 1 and mask[FULL_BRAKE_INDEX]:
            self.forced_brake_steps += 1

    def _record(self, mask: np.ndarray) -> None:
        self.allowed_actions_total += int(mask[:ACC_ACTIONS].sum()) * int(mask[ACC_ACTIONS:].sum())
