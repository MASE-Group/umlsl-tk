"""Drive UMLSL-Edit and capture real window screenshots with QWidget.grab().

Usage: python edit_shots.py OUT_DIR SCENE [phase]
phase "main"    : sample scene, dialogs, simulate prompt
phase "handoff" : open a UMLSL-Sim snapshot like 'Open in UMLSL-Edit' does
"""
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from umlsl_edit.controllers import ApplicationController
from umlsl_edit.view.ui.main_window import MainWindow
from umlsl_edit.view.ui.lists.edit_dialogs.edit_car_dialog import EditCarDialog
from umlsl_edit.view.ui.lists.edit_dialogs.edit_query_dialog import EditQueryDialog
from umlsl_edit.view.ui.lists.edit_dialogs.edit_road_dialog import EditRoadDialog



def main():
    OUT, SCENE = sys.argv[1], sys.argv[2]
    PHASE = sys.argv[3] if len(sys.argv) > 3 else "main"
    os.makedirs(OUT, exist_ok=True)

    app = QApplication(sys.argv)
    ac = ApplicationController()
    win = MainWindow(ac)
    win.resize(int(os.environ.get('W','1600')), int(os.environ.get('H','1000')))
    win.show()
    cc = ac.command_controller

    steps = []


    def step(delay_ms):
        def deco(fn):
            steps.append((delay_ms, fn))
            return fn
        return deco


    def run_steps(i=0):
        if i >= len(steps):
            QTimer.singleShot(300, app.quit)
            return
        delay, fn = steps[i]

        def go():
            try:
                fn()
            except Exception as exc:  # keep going, report
                print("STEP FAILED", fn.__name__, exc, flush=True)
            run_steps(i + 1)
        QTimer.singleShot(delay, go)


    def save(widget, name):
        pix = widget.grab()
        path = os.path.join(OUT, name)
        pix.save(path)
        print("saved", path, pix.width(), pix.height(), flush=True)


    def car_by_name(name):
        for uid, car in ac.data_controller.get_all_cars().items():
            if car.name == name:
                return uid, car
        raise KeyError(name)


    def query_for(car_uid):
        for q in cc.umlsl_queries_model.get_queries().values():
            if q.assigned_car_uid == car_uid:
                return q
        raise KeyError(car_uid)


    state = {}

    if PHASE == "main":
        @step(500)
        def load():
            cc.load_traffic_snapshot(SCENE)

        @step(9000)
        def select_e():
            uid, _ = car_by_name("E")
            cc.add_umlsl_query(uid, False, "<hchop{re{E}}{cs}>")
            state["e"] = uid

        @step(9000)
        def select_e2():
            ac.view_event_handler.entity_selected_view(state["e"])

        @step(1500)
        def shot_main():
            save(win, "edit_main.png")

        @step(200)
        def road_dialog():
            d = EditRoadDialog(None, parent=win, application_controller=ac)
            d.show()
            state["d"] = d

        @step(1200)
        def shot_road():
            save(state["d"], "edit_add_road.png")
            state["d"].close()

        @step(200)
        def car_dialog():
            _, car = car_by_name("A")
            d = EditCarDialog(car, parent=win, application_controller=ac)
            d.show()
            state["d"] = d

        @step(1200)
        def shot_car():
            save(state["d"], "edit_car.png")
            state["d"].close()

        @step(200)
        def query_dialog():
            uid, _ = car_by_name("E")
            d = EditQueryDialog(query_for(uid), application_controller=ac, parent=win)
            d.show()
            state["d"] = d

        @step(5000)
        def shot_query():
            save(state["d"], "edit_query.png")
            state["d"]._help_dialog.show()
            state["help"] = state["d"]._help_dialog

        @step(1500)
        def shot_help():
            save(state["help"], "edit_query_help.png")
            state["help"].close()
            state["d"].close()

        @step(500)
        def simulate():
            def grab_prompt():
                modal = QApplication.activeModalWidget()
                if modal is None:
                    QTimer.singleShot(300, grab_prompt)
                    return
                save(modal, "edit_simulate_prompt.png")
                modal.reject()  # the simulator is started by the Sim driver instead
            QTimer.singleShot(1200, grab_prompt)
            win.global_controls._on_simulate()

        @step(500)
        def export_copy():
            cc.export_snapshot(os.path.join(OUT, "_export_check.json"))
            print("exported", flush=True)

    elif PHASE == "menu":
        @step(500)
        def load_m():
            cc.load_traffic_snapshot(SCENE)

        @step(1500)
        def popup():
            from PySide6.QtCore import QPoint
            win.menuFile.popup(win.mapToGlobal(QPoint(0, 20)))

        @step(1200)
        def shot_menu():
            save(win.menuFile, "edit_file_menu.png")
            win.menuFile.close()

    elif PHASE == "handoff":
        @step(500)
        def open_snapshot():
            def grab_notes():
                modal = QApplication.activeModalWidget()
                if modal is None:
                    QTimer.singleShot(300, grab_notes)
                    return
                save(modal, "edit_import_notes.png")
                modal.accept()
            QTimer.singleShot(2500, grab_notes)
            win.global_controls.open_from_simulator(SCENE)

        @step(1500)
        def add_queries():
            cars = ac.data_controller.get_all_cars()
            names = sorted(c.name for c in cars.values())
            print("cars:", names, flush=True)
            ego = os.environ.get("EGO", names[0])
            uid, _ = car_by_name(ego)
            cc.add_umlsl_query(uid, False, f"neg exists c: (c != {ego} and < re{{c}} and re{{{ego}}} >)")
            cc.add_umlsl_query(uid, False, f"<hchop{{re{{{ego}}}}}{{free and l > 2}}>")
            state["ego"] = uid

        @step(9000)
        def select_ego():
            ac.view_event_handler.entity_selected_view(state["ego"])

        @step(1500)
        def shot_handoff():
            save(win, "edit_handoff.png")

    QTimer.singleShot(0, run_steps)
    app.exec()


if __name__ == "__main__":
    main()
