"""The safety controller and the action shield built on it.

`SafetyController` answers what is safe rather than what is best: the maximum
acceleration that still lets the car stop in the space it holds, and which lane
changes complete without a conflict. `ActionShield` turns those answers into a
Gymnasium action mask, which is how safety reaches RL training.
"""
