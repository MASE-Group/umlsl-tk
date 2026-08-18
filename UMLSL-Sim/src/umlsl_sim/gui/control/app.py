"""The control window: a control panel plus an embedded simulation viewport.

Layout (left → right):

* a fixed-width control panel with dropdowns (scenario, RL mode, RL algorithm,
  observation model, reward, saved model), a players field, a "show
  reservations" toggle, action buttons (Run / Play-Pause / Rerun / Save) and a
  status log;
* the live simulation, rendered into the remaining area.

All simulation stepping happens on the pyglet clock owned by this window, so the
simulation genuinely runs *inside* the GUI.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

import pyglet
from pyglet.text import Label
from pyglet.window import key

from umlsl_sim.scenario.loader import load_scenario
from umlsl_sim.gui.control import rl_support, theme
from umlsl_sim.gui.control.scene_renderer import SceneRenderer
from umlsl_sim.gui.control.scenario_saver import save_current_scenario, scenarios_dir
from umlsl_sim.gui.control.sim_engine import STEP_INTERVAL, SimulationEngine
from umlsl_sim.gui.control.widgets import Button, Checkbox, Dropdown, LogView, TextField

log = logging.getLogger(__name__)

WIN_W = 1300
WIN_H = 880

# Height of the strip reserved at the top of the viewport card for the banner
# that names the car the RL agent drives. The scene is letterboxed into the
# space below it, so the banner never overlaps the simulation.
BANNER_H = 26


def list_scenarios() -> List[str]:
    d = scenarios_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def read_scenario_meta(stem: str) -> dict:
    try:
        with open(scenarios_dir() / f"{stem}.json") as f:
            data = json.load(f)
        return {
            "players": int(data.get("players", 8)),
            "scenario_name": data.get("scenario_name", stem),
        }
    except Exception:
        return {"players": 8, "scenario_name": stem}


class ControlWindow(pyglet.window.Window):
    def __init__(self) -> None:
        super().__init__(width=WIN_W, height=WIN_H, caption="UMLSL-Sim", resizable=False)
        from pyglet.gl import glClearColor

        glClearColor(*[c / 255 for c in theme.BACKGROUND], 1.0)

        # centre on screen
        screen = self.display.get_default_screen()
        self.set_location((screen.width - WIN_W) // 2, max(0, (screen.height - WIN_H) // 2))

        self.engine = SimulationEngine()
        self.engine.set_finish_callback(lambda msg: None)  # status surfaced via _tick
        self.scene = SceneRenderer(self)
        self.rl_worker = rl_support.RLWorker()

        # batches / groups
        self.chrome_batch = pyglet.graphics.Batch()
        self.ui_batch = pyglet.graphics.Batch()
        self.g_base = pyglet.graphics.Group(order=0)
        self.g_overlay = pyglet.graphics.Group(order=10)

        # interaction bookkeeping
        self.dropdowns: List[Dropdown] = []
        self.buttons: List[Button] = []
        self.checkboxes: List[Checkbox] = []
        self.text_fields: List[TextField] = []
        self.open_dropdown: Optional[Dropdown] = None
        self.focused_field: Optional[TextField] = None
        self._captions: List[Label] = []
        self._rl_captions: List[Label] = []
        self._model_caption: Optional[Label] = None
        self._last_status = ""

        self._build_chrome()
        self._build_controls()
        self._apply_mode_visibility()
        self._on_scenario_change(self.scenario_dd.selected, initial=True)
        self._sync_controls()

        if not rl_support.RUNTIME_AVAILABLE:
            self.log("RL runtime not installed — plain simulation only.")
            self.log(rl_support.RUNTIME_REASON)
        self.log("Ready. Pick a scenario and press Run.")

        pyglet.clock.schedule_interval(self.engine.update, STEP_INTERVAL)
        pyglet.clock.schedule_interval(self._tick, 0.1)

    # --- construction -----------------------------------------------------
    @property
    def viewport(self):
        vx = theme.PANEL_WIDTH + 16
        vy = 16
        return (vx, vy, self.width - vx - 16, self.height - 32)

    @property
    def scene_viewport(self):
        """The viewport card minus the banner strip: where the scene is drawn."""
        vx, vy, vw, vh = self.viewport
        return (vx, vy, vw, vh - BANNER_H)

    def _build_chrome(self) -> None:
        self._panel = pyglet.shapes.Rectangle(
            0, 0, theme.PANEL_WIDTH, self.height, color=theme.PANEL,
            batch=self.chrome_batch, group=self.g_base,
        )
        vx, vy, vw, vh = self.viewport
        self._viewport_card = pyglet.shapes.Rectangle(
            vx, vy, vw, vh, color=theme.LAYER, batch=self.chrome_batch, group=self.g_base,
        )
        sx, sy, sw, sh = self.scene_viewport
        self._hint = Label(
            "Choose a scenario and press Run",
            font_name=theme.FONT, font_size=16, color=(*theme.LAYER_ACTIVE, 255),
            x=sx + sw / 2, y=sy + sh / 2, anchor_x="center", anchor_y="center",
            batch=self.ui_batch, group=self.g_base,
        )
        # Sits in the reserved strip above the scene; only shown while a trained
        # model is driving (RLMode.LOAD_TRAINED_MODEL).
        self._agent_banner = Label(
            "", font_name=theme.FONT, font_size=theme.FONT_SIZE, weight="bold",
            color=(*theme.TEXT, 255),
            x=vx + vw / 2, y=vy + vh - BANNER_H / 2,
            anchor_x="center", anchor_y="center",
            batch=self.ui_batch, group=self.g_base,
        )
        self._agent_banner.visible = False

    def _add_caption(self, text: str, x: float, y: float, rl: bool = False, model: bool = False) -> Label:
        lbl = Label(
            text, font_name=theme.FONT, font_size=theme.FONT_SIZE_SMALL, weight="bold",
            color=(*theme.MUTED_TEXT, 255), x=x, y=y, anchor_x="left", anchor_y="top",
            batch=self.ui_batch, group=self.g_base,
        )
        self._captions.append(lbl)
        if rl:
            self._rl_captions.append(lbl)
        if model:
            self._model_caption = lbl
        return lbl

    def _build_controls(self) -> None:
        inner_x = theme.PANEL_PAD
        inner_w = theme.PANEL_WIDTH - 2 * theme.PANEL_PAD
        y = self.height - theme.PANEL_PAD

        # Title
        Label(
            "UMLSL-Sim", font_name=theme.FONT, font_size=theme.FONT_SIZE_TITLE, weight="bold",
            color=(*theme.TEXT, 255), x=inner_x, y=y, anchor_x="left", anchor_y="top",
            batch=self.ui_batch, group=self.g_base,
        )
        y -= 36

        def caption(text, rl=False, model=False):
            nonlocal y
            self._add_caption(text, inner_x, y, rl=rl, model=model)
            y -= 18

        def slot(h):
            nonlocal y
            y -= h
            yb = y
            y -= theme.GAP
            return yb

        # Scenario
        caption("Scenario")
        yb = slot(34)
        self.scenario_dd = self._add_dropdown(
            inner_x, yb, inner_w, 34, list_scenarios() or ["<none>"], self._on_scenario_change,
            selected="two_crossings" if "two_crossings" in list_scenarios() else None,
        )

        # Players
        caption("Players (NPCs)")
        yb = slot(34)
        self.players_field = self._add_text_field(
            inner_x, yb, inner_w, 34, "", placeholder="auto",
            allowed="0123456789", max_len=4,
        )

        # Show reservations
        yb = slot(24)
        self.show_res_cb = Checkbox(
            inner_x, yb, 20, "Show reservations", True, lambda v: None,
            self.ui_batch, self.g_base,
        )
        self.checkboxes.append(self.show_res_cb)

        y -= 4
        # RL mode
        caption("RL mode")
        yb = slot(34)
        self.rlmode_dd = self._add_dropdown(
            inner_x, yb, inner_w, 34, rl_support.rl_mode_labels(), self._on_rlmode_change,
        )

        # RL algorithm (also selects the safety mechanism: MASKABLE_PPO shields)
        caption("RL algorithm / safety mechanism", rl=True)
        yb = slot(34)
        self.algo_dd = self._add_dropdown(
            inner_x, yb, inner_w, 34, rl_support.algorithm_names() or ["—"], self._on_algo_change,
        )

        # Observation model
        caption("Observation model", rl=True)
        yb = slot(34)
        self.obs_dd = self._add_dropdown(
            inner_x, yb, inner_w, 34, rl_support.observation_names() or ["—"], self._on_rlconfig_change,
        )

        # Reward
        caption("Reward", rl=True)
        yb = slot(34)
        self.reward_dd = self._add_dropdown(
            inner_x, yb, inner_w, 34, rl_support.reward_names() or ["—"], self._on_rlconfig_change,
        )

        # Saved model
        caption("Saved model", model=True)
        yb = slot(34)
        self.model_dd = self._add_dropdown(
            inner_x, yb, inner_w, 34, ["—"], lambda v: None,
        )

        y -= 6
        # Run
        yb = slot(38)
        self.run_btn = self._add_button(
            inner_x, yb, inner_w, 38, "Run", self._on_run, kind=Button.KIND_PRIMARY,
        )

        # Play/Pause + Rerun
        yb = slot(36)
        half = (inner_w - theme.GAP) / 2
        self.play_btn = self._add_button(inner_x, yb, half, 36, "Play / Pause", self._on_play_pause)
        self.rerun_btn = self._add_button(inner_x + half + theme.GAP, yb, half, 36, "Rerun", self._on_rerun)

        # Save
        caption("New scenario name")
        yb = slot(30)
        self.name_field = self._add_text_field(
            inner_x, yb, inner_w, 30, "", placeholder="e.g. my_scenario", max_len=40,
        )
        yb = slot(36)
        self.save_btn = self._add_button(
            inner_x, yb, inner_w, 36, "Save paused scenario", self._on_save,
        )

        # Log fills remaining space
        y -= 4
        log_bottom = 16
        log_h = max(60, y - log_bottom)
        self.log_view = LogView(
            inner_x, log_bottom, inner_w, log_h, self.ui_batch, self.g_base, title="Status",
        )

    # widget factory helpers
    def _add_dropdown(self, x, y, w, h, options, on_change, selected=None) -> Dropdown:
        dd = Dropdown(x, y, w, h, options, on_change, self.ui_batch, self.g_base, self.g_overlay, selected)
        self.dropdowns.append(dd)
        return dd

    def _add_button(self, x, y, w, h, text, on_click, kind=Button.KIND_DEFAULT) -> Button:
        b = Button(x, y, w, h, text, on_click, self.ui_batch, self.g_base, kind=kind)
        self.buttons.append(b)
        return b

    def _add_text_field(self, x, y, w, h, value, placeholder="", allowed=None, max_len=40) -> TextField:
        tf = TextField(x, y, w, h, value, self.ui_batch, self.g_base,
                       placeholder=placeholder, allowed=allowed, max_len=max_len)
        self.text_fields.append(tf)
        return tf

    # --- logging ----------------------------------------------------------
    def log(self, message: str) -> None:
        self.log_view.append(message)

    # --- control-state sync ----------------------------------------------
    def _current_rl_enums(self):
        try:
            algo = rl_support.RLAlgorithmType[self.algo_dd.selected]
            obs = rl_support.ObservationModelType[self.obs_dd.selected]
            reward = rl_support.RewardType[self.reward_dd.selected]
            return algo, obs, reward
        except Exception:
            return None, None, None

    def _apply_mode_visibility(self) -> None:
        mode = rl_support.mode_from_label(self.rlmode_dd.selected)
        rl_on = mode is not None
        needs_model = mode is not None and mode.name == "LOAD_TRAINED_MODEL"
        for w in (self.algo_dd, self.obs_dd, self.reward_dd):
            w.set_visible(rl_on)
        for cap in self._rl_captions:
            cap.visible = rl_on
        self.model_dd.set_visible(needs_model)
        if self._model_caption is not None:
            self._model_caption.visible = needs_model

    def _sync_controls(self) -> None:
        active = self.engine.active
        self.play_btn.set_enabled(active and not self.engine.finished)
        self.rerun_btn.set_enabled(active or self.engine.can_restart)
        can_save = active and (self.engine.paused or self.engine.finished) and self.engine.game_model is not None
        self.save_btn.set_enabled(bool(can_save))
        self.run_btn.set_enabled(not self.rl_worker.running)
        self._hint.visible = not active
        self._sync_agent_banner()
        # reflect engine status changes in the log
        if self.engine.status != self._last_status:
            self._last_status = self.engine.status
            if active:
                self.log(self.engine.status)

    def _sync_agent_banner(self) -> None:
        name = self.engine.agent_car_name
        if name is None:
            self._agent_banner.visible = False
            return
        text = f"The RL agent controls the {name} car"
        if self._agent_banner.text != text:
            self._agent_banner.text = text
        self._agent_banner.visible = True

    # --- clock ------------------------------------------------------------
    def _tick(self, _dt: float) -> None:
        for level, msg in self.rl_worker.drain():
            if level == "done":
                # a training/optimize job finished: surface any new saved model
                self._refresh_model_dd()
                continue
            if msg:
                self.log(f"[{level}] {msg}" if level in ("warn", "error") else msg)
        self._sync_controls()

    # --- event handlers: dropdown callbacks -------------------------------
    def _on_scenario_change(self, stem: str, initial: bool = False) -> None:
        meta = read_scenario_meta(stem)
        self.players_field.set_value("")
        self.players_field.placeholder = f"auto ({meta['players']})"
        self.players_field._label.text = self.players_field._display()
        self.players_field._label.color = self.players_field._text_color()
        self._refresh_model_dd()

    def _on_rlmode_change(self, _label: str) -> None:
        self._apply_mode_visibility()
        self._refresh_model_dd()

    def _on_rlconfig_change(self, _value: str) -> None:
        self._refresh_model_dd()

    def _on_algo_change(self, value: str) -> None:
        # The algorithm dropdown doubles as the safety-mechanism switch, so say
        # in the log which mechanism the user just picked.
        self._refresh_model_dd()
        description = rl_support.algorithm_description(value)
        if description:
            self.log(description)

    def _refresh_model_dd(self) -> None:
        if not rl_support.ENUMS_AVAILABLE:
            self.model_dd.set_options(["—"], selected="—")
            return
        meta = read_scenario_meta(self.scenario_dd.selected)
        ids = rl_support.list_model_ids(
            meta["scenario_name"], self.algo_dd.selected, self.obs_dd.selected, self.reward_dd.selected
        )
        if ids:
            self.model_dd.set_options(ids, selected=ids[0])
        else:
            self.model_dd.set_options(["—"], selected="—")

    # --- action buttons ---------------------------------------------------
    def _resolve_players(self, scenario: dict) -> int:
        text = self.players_field.value.strip()
        if text:
            try:
                value = int(text)
                if value >= 1:
                    return value
            except ValueError:
                pass
        return scenario["players"]

    def _on_run(self) -> None:
        if self.rl_worker.running:
            self.log("[warn] An RL job is running; wait for it to finish.")
            return
        stem = self.scenario_dd.selected
        try:
            scenario = load_scenario(stem)
        except Exception as exc:
            self.log(f"[error] Could not load scenario '{stem}': {exc}")
            return

        players = self._resolve_players(scenario)
        show_res = self.show_res_cb.checked
        mode = rl_support.mode_from_label(self.rlmode_dd.selected)

        if mode is None:
            try:
                self.engine.start_plain(scenario["roads"], players, scenario["predefined_cars"], show_res)
                self.log(f"Started simulation: {stem} ({players} NPCs).")
            except Exception as exc:
                self.log(f"[error] Failed to start: {exc}")
            return

        if not rl_support.RUNTIME_AVAILABLE:
            self.log(f"[error] {rl_support.RUNTIME_REASON}")
            return

        algo, obs, reward = self._current_rl_enums()
        if algo is None:
            self.log("[error] RL algorithm/observation/reward not available.")
            return

        if mode.name == "LOAD_TRAINED_MODEL":
            model_id = self.model_dd.selected
            if not model_id or model_id == "—":
                self.log("[error] No saved model for this configuration. Train one first.")
                return
            try:
                self.engine.start_rl_eval(
                    scenario["roads"], players, scenario["predefined_cars"], show_res,
                    scenario["scenario_name"], algo, obs, reward, model_id,
                )
                self.log(f"Running trained model '{model_id}'.")
            except Exception as exc:
                self.log(f"[error] Failed to load model: {exc}")
            return

        # TRAIN / OPTIMIZE / OPTIMIZE_AND_TRAIN -> background, headless
        self.engine.clear()
        started = self.rl_worker.start(
            roads=scenario["roads"], players=players, predefined_cars=scenario["predefined_cars"],
            scenario_name=scenario["scenario_name"], rl_mode=mode,
            rl_algorithm_type=algo, observation_model_type=obs, reward_type=reward,
        )
        if started:
            self.log(f"Launched {mode.name} with {algo.name} / {reward.name} (headless). "
                     "Watch the terminal for progress.")

    def _on_play_pause(self) -> None:
        self.engine.toggle_pause()

    def _on_rerun(self) -> None:
        self.engine.rerun()
        self.log("Rerun.")

    def _on_save(self) -> None:
        if self.engine.game_model is None:
            self.log("[warn] Nothing to save — run a simulation first.")
            return
        if not (self.engine.paused or self.engine.finished):
            self.log("[warn] Pause the simulation before saving (press Space).")
            return
        name = self.name_field.value.strip() or f"{self.scenario_dd.selected}_saved"
        try:
            result = save_current_scenario(self.engine.game_model, name)
        except FileExistsError as exc:
            self.log(f"[warn] '{exc}' already exists. Choose a different name.")
            return
        except Exception as exc:
            self.log(f"[error] Save failed: {exc}")
            return

        self.log(f"Saved {result.n_cars} cars to {result.path.name}.")
        if result.n_agents:
            self.log(f"Note: {result.n_agents} AGENT car(s) — load with an RL mode.")
        if result.snapped:
            self.log(f"Note: snapped mid-crossing car(s): {', '.join(result.snapped)}.")
        # make the new scenario selectable without restarting
        self.scenario_dd.set_options(list_scenarios(), selected=self.scenario_dd.selected)

    # --- rendering --------------------------------------------------------
    def on_draw(self) -> None:
        self.clear()
        self.chrome_batch.draw()
        self.scene.draw(self.scene_viewport, self.engine.world(), self.engine.flash_count,
                        self.show_res_cb.checked)
        self.ui_batch.draw()

    # --- mouse ------------------------------------------------------------
    def on_mouse_motion(self, x, y, dx, dy) -> None:
        if self.open_dropdown is not None:
            self.open_dropdown.on_mouse_motion(x, y)
        for w in self.buttons + self.dropdowns + self.checkboxes:
            w.on_mouse_motion(x, y)

    def on_mouse_press(self, x, y, button, modifiers) -> None:
        # 1. an open dropdown intercepts the click
        if self.open_dropdown is not None:
            dd = self.open_dropdown
            if dd.menu_contains(x, y):
                dd.choose_at(x, y)
                self.open_dropdown = None
                return
            dd.close()
            self.open_dropdown = None
            if dd.contains(x, y):
                return  # clicked the face → treat as toggle-close

        # 2. focus management for text fields
        clicked_field = next(
            (w for w in self.text_fields if w.visible and w.enabled and w.contains(x, y)), None
        )
        if self.focused_field is not None and self.focused_field is not clicked_field:
            self.focused_field.set_focus(False)
        self.focused_field = clicked_field
        if clicked_field is not None:
            clicked_field.set_focus(True)
            return

        # 3. dropdown faces open their menu
        for dd in self.dropdowns:
            if dd.visible and dd.enabled and dd.contains(x, y):
                dd.open()
                self.open_dropdown = dd
                return

        # 4. buttons / checkboxes
        for w in self.buttons + self.checkboxes:
            if w.on_mouse_press(x, y, button):
                return

    def on_mouse_release(self, x, y, button, modifiers) -> None:
        for b in self.buttons:
            b.on_mouse_release(x, y, button)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers) -> None:
        if self.open_dropdown is not None:
            self.open_dropdown.on_mouse_motion(x, y)

    # --- keyboard ---------------------------------------------------------
    def on_text(self, text) -> None:
        if self.focused_field is not None:
            self.focused_field.insert(text)

    def on_key_press(self, symbol, modifiers) -> None:
        if self.focused_field is not None:
            if symbol == key.BACKSPACE:
                self.focused_field.backspace()
            elif symbol in (key.ENTER, key.RETURN, key.ESCAPE):
                self.focused_field.set_focus(False)
                self.focused_field = None
            return  # swallow keys while typing (so Space doesn't toggle pause)

        if symbol == key.SPACE:
            self.engine.toggle_pause()
        elif symbol == key.ESCAPE:
            if self.open_dropdown is not None:
                self.open_dropdown.close()
                self.open_dropdown = None


def launch() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s",
    )
    ControlWindow()
    pyglet.app.run()


if __name__ == "__main__":
    launch()
