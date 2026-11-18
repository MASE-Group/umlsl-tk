"""Drive the UMLSL-Sim control GUI and save real frame-buffer screenshots.

Usage: python sim_shots.py OUT_DIR PHASE
PHASE one      : sim_demo_one_crossing, started like UMLSL-Edit's "Simulate in UMLSL-Sim"
PHASE two      : two_crossings plain run, then the RL / shield / reward controls
PHASE agent    : two_crossings with a trained MaskablePPO agent (needs a saved model)
PHASE handoff  : two_crossings, then "Open in UMLSL-Edit" (editor start stubbed out;
                 the edit driver opens the saved file the same way the editor does)
"""
import os
import sys

import pyglet

import umlsl_sim.gui.control.app as app_mod
from umlsl_sim.gui.control import rl_support

OUT, PHASE = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

pending = []


class _FakeEditor:
    def failure(self):
        return None


if PHASE == "handoff":
    app_mod.open_in_editor = lambda path: _FakeEditor()

scenario = "sim_demo_one_crossing" if PHASE == "one" else "two_crossings"
autorun = PHASE in ("one", "two", "handoff")
win = app_mod.ControlWindow(scenario=scenario, autorun=autorun)

_orig_draw = win.on_draw


def on_draw():
    _orig_draw()
    while pending:
        name = pending.pop(0)
        path = os.path.join(OUT, name)
        pyglet.image.get_buffer_manager().get_color_buffer().save(path)
        print("saved", path, flush=True)


win.on_draw = on_draw


def shot(name):
    pending.append(name)


timeline = []


def at(t):
    def deco(fn):
        timeline.append((t, fn))
        return fn
    return deco


def open_dd(dd):
    dd.open()
    win.open_dropdown = dd


def close_dd():
    if win.open_dropdown is not None:
        win.open_dropdown.close()
        win.open_dropdown = None


if PHASE == "one":
    at(0.3)(lambda: shot("sim_one_start.png"))
    at(1.0)(lambda: win.engine.toggle_pause())
    at(1.3)(lambda: shot("sim_one_paused_start.png"))
    at(1.6)(lambda: win.engine.toggle_pause())
    at(4.0)(lambda: shot("sim_one_t4.png"))
    at(8.0)(lambda: shot("sim_one_t8.png"))
    at(9.0)(lambda: pyglet.app.exit())

elif PHASE == "two":
    at(6.0)(lambda: shot("sim_two_running.png"))
    at(6.5)(lambda: win.engine.toggle_pause())

    @at(7.0)
    def rl_menu():
        open_dd(win.rlmode_dd)
        shot("sim_rl_modes.png")

    @at(8.0)
    def shield():
        close_dd()
        win.rlmode_dd.set_selected("Train", fire=True)
        win.algo_dd.set_selected("MASKABLE_PPO", fire=True)
        win.reward_dd.set_selected("INITIAL_REWARD", fire=True)
        shot("sim_shield_config.png")

    @at(9.0)
    def algo_menu():
        open_dd(win.algo_dd)
        shot("sim_algo_menu.png")

    @at(10.0)
    def reward_menu():
        close_dd()
        win.algo_dd.set_selected("PPO", fire=True)
        open_dd(win.reward_dd)
        shot("sim_reward_menu.png")

    at(11.0)(lambda: pyglet.app.exit())

elif PHASE == "agent":
    @at(0.5)
    def load_agent():
        win.rlmode_dd.set_selected("Load trained model", fire=True)
        win.algo_dd.set_selected("MASKABLE_PPO", fire=True)
        win.reward_dd.set_selected("INITIAL_REWARD", fire=True)
        win._refresh_model_dd()
        print("model:", win.model_dd.selected, flush=True)
        win._on_run()

    at(8.0)(lambda: shot("sim_agent.png"))
    at(9.0)(lambda: pyglet.app.exit())

elif PHASE == "handoff":
    @at(7.0)
    def handoff():
        win.name_field.set_value("slides_handoff")
        win._on_open_in_editor()

    at(8.0)(lambda: shot("sim_handoff.png"))
    at(9.0)(lambda: pyglet.app.exit())

for t, fn in timeline:
    pyglet.clock.schedule_once(lambda _dt, f=fn: f(), t)

pyglet.app.run()
