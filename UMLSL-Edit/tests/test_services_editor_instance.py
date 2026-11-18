"""Handing a snapshot from UMLSL-Sim to an editor window that is already open."""
import os
import subprocess
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication

from umlsl_edit.services.editor_instance import (
    EditorInstanceServer,
    forward_to_running_editor,
    import_request,
)
from umlsl_edit.view.ui import global_controls
from umlsl_edit.view.ui.global_controls import GlobalControls

CLIENT = (
    "import sys\n"
    "from PySide6.QtCore import QCoreApplication\n"
    "app = QCoreApplication([])\n"
    "from umlsl_edit.services.editor_instance import forward_to_running_editor\n"
    "sys.exit(0 if forward_to_running_editor(sys.argv[1], sys.argv[2]) else 3)\n"
)


def unique_name(test: unittest.TestCase) -> str:
    # Short: a local socket's full path (temp folder + name) is limited to about 100 characters.
    return f"ue-test-{os.getpid()}-{abs(hash(test._testMethodName)) % 10000}"


class TestImportRequest(unittest.TestCase):
    def test_reads_the_file_after_the_flag(self):
        self.assertEqual(import_request(["main.py", "--import-from-sim", "/tmp/a.json"]), "/tmp/a.json")

    def test_plain_launches_are_no_request(self):
        self.assertIsNone(import_request(["main.py"]))
        self.assertIsNone(import_request(["main.py", "scene.json"]))
        self.assertIsNone(import_request(["main.py", "--import-from-sim"]))


class TestEditorInstanceServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_no_open_editor_takes_nothing(self):
        self.assertFalse(forward_to_running_editor("/tmp/a.json", unique_name(self)))

    def test_the_open_editor_receives_the_file(self):
        name = unique_name(self)
        server = EditorInstanceServer(name=name)
        self.assertTrue(server.listen())
        received = []
        server.import_requested.connect(received.append)
        try:
            client = subprocess.Popen([sys.executable, "-c", CLIENT, "/tmp/from_sim.json", name])
            deadline = time.monotonic() + 15
            while (client.poll() is None or not received) and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
        finally:
            server.close()
        self.assertEqual(client.wait(timeout=5), 0)
        self.assertEqual(received, ["/tmp/from_sim.json"])

    def test_a_second_editor_leaves_the_first_one_listening(self):
        name = unique_name(self)
        first, second = EditorInstanceServer(name=name), EditorInstanceServer(name=name)
        try:
            self.assertTrue(first.listen())
            self.assertFalse(second.listen())
            self.assertTrue(first.is_listening)
        finally:
            first.close()
            second.close()


class TestOpenFromSimulator(unittest.TestCase):
    """The open editor asks to save unsaved changes before the snapshot replaces them."""

    def open(self, changed, answer=None, saved=True, import_error=None):
        controls = MagicMock()
        controller = controls.application_controller.command_controller
        controller.get_data_changed_since_last_save.return_value = changed
        controller.import_snapshot.return_value = ["a note"]
        if import_error is not None:
            controller.import_snapshot.side_effect = import_error
        controls._on_save.return_value = saved
        with patch.object(global_controls, "SaveChangesDialog") as dialog, \
                patch.object(global_controls, "WarningDialog") as warning:
            dialog.SAVE, dialog.DISCARD, dialog.CANCEL = 2, 1, 0
            dialog.return_value.exec.return_value = answer
            GlobalControls.open_from_simulator(controls, "/tmp/demo_paused.json")
        return controls, controller, dialog, warning

    def test_without_unsaved_changes_it_opens_at_once(self):
        controls, controller, dialog, _ = self.open(changed=False)
        dialog.assert_not_called()
        controller.import_snapshot.assert_called_once_with("/tmp/demo_paused.json")
        controls.show_import_notes.assert_called_once_with(["a note"])
        controls._bring_window_to_front.assert_called_once()

    def test_cancel_keeps_the_current_scenario(self):
        _, controller, dialog, _ = self.open(changed=True, answer=0)
        dialog.assert_called_once()
        controller.import_snapshot.assert_not_called()

    def test_dont_save_opens_without_saving(self):
        controls, controller, _, _ = self.open(changed=True, answer=1)
        controls._on_save.assert_not_called()
        controller.import_snapshot.assert_called_once()

    def test_save_saves_first(self):
        controls, controller, _, _ = self.open(changed=True, answer=2)
        controls._on_save.assert_called_once()
        controller.import_snapshot.assert_called_once()

    def test_a_save_that_did_not_happen_keeps_the_current_scenario(self):
        _, controller, _, _ = self.open(changed=True, answer=2, saved=False)
        controller.import_snapshot.assert_not_called()

    def test_a_snapshot_that_cannot_be_read_is_reported(self):
        from umlsl_edit.commands.command import CommandValidationError
        controls, _, _, warning = self.open(changed=False, import_error=CommandValidationError("bad file"))
        warning.assert_called_once()
        self.assertIn("bad file", warning.call_args.args[1])
        controls.show_import_notes.assert_not_called()

    def test_a_snapshot_waits_while_a_dialog_is_open(self):
        controls = MagicMock()
        with patch.object(global_controls.QApplication, "activeModalWidget", return_value=object()), \
                patch.object(global_controls.QTimer, "singleShot") as later:
            GlobalControls.receive_from_simulator(controls, "/tmp/demo_paused.json")
        controls.open_from_simulator.assert_not_called()
        later.assert_called_once()
        with patch.object(global_controls.QApplication, "activeModalWidget", return_value=None):
            GlobalControls.receive_from_simulator(controls, "/tmp/demo_paused.json")
        controls.open_from_simulator.assert_called_once_with("/tmp/demo_paused.json")


if __name__ == "__main__":
    unittest.main()
