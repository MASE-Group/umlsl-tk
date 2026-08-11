import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from umlsl_edit.commands.command import CommandValidationError
from umlsl_edit.commands.persistence.load_traffic_snapshot import LoadTrafficSnapshot
from umlsl_edit.commands.persistence.save_as_traffic_snapshot import SaveAsTrafficSnapshot
from umlsl_edit.commands.persistence.save_traffic_snapshot import SaveTrafficSnapshot


class TestSaveTrafficSnapshot(unittest.TestCase):
    def test_execute_requires_file_path(self):
        cmd = SaveTrafficSnapshot(file_path="", traffic_snapshot_reader=MagicMock(), umlsl_queries=MagicMock())
        with self.assertRaises(CommandValidationError):
            cmd.execute()

    def test_execute_serializes_and_writes_file(self):
        reader = MagicMock()
        queries = MagicMock()
        payload = {"meta": {"version": 1}, "roads": [], "cars": [], "queries": []}

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch(
                "umlsl_edit.commands.persistence.save_traffic_snapshot.PersistenceService.serialize",
                autospec=True,
            ) as serialize:
                serialize.return_value = payload

                cmd = SaveTrafficSnapshot(file_path=tmp_path, traffic_snapshot_reader=reader, umlsl_queries=queries)
                cmd.execute()

                serialize.assert_called_once_with(snapshot=reader, queries=queries)

            with open(tmp_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            self.assertEqual(data, payload)
        finally:
            os.remove(tmp_path)

    def test_execute_raises_on_serialize_error(self):
        reader = MagicMock()
        queries = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch(
                "umlsl_edit.commands.persistence.save_traffic_snapshot.PersistenceService.serialize",
                autospec=True,
            ) as serialize:
                serialize.side_effect = ValueError("bad payload")

                cmd = SaveTrafficSnapshot(file_path=tmp_path, traffic_snapshot_reader=reader, umlsl_queries=queries)
                with self.assertRaises(CommandValidationError):
                    cmd.execute()
        finally:
            os.remove(tmp_path)


class TestSaveAsTrafficSnapshot(unittest.TestCase):
    def test_execute_requires_file_path(self):
        cmd = SaveAsTrafficSnapshot(file_path="", traffic_snapshot_reader=MagicMock(), umlsl_queries=MagicMock())
        with self.assertRaises(CommandValidationError):
            cmd.execute()

    def test_execute_serializes_and_writes_file(self):
        reader = MagicMock()
        queries = MagicMock()
        payload = {"meta": {"version": 1}, "roads": [], "cars": [], "queries": []}

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch(
                "umlsl_edit.commands.persistence.save_as_traffic_snapshot.PersistenceService.serialize",
                autospec=True,
            ) as serialize:
                serialize.return_value = payload

                cmd = SaveAsTrafficSnapshot(file_path=tmp_path, traffic_snapshot_reader=reader, umlsl_queries=queries)
                cmd.execute()

                serialize.assert_called_once_with(snapshot=reader, queries=queries)

            with open(tmp_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            self.assertEqual(data, payload)
        finally:
            os.remove(tmp_path)

    def test_execute_raises_on_serialize_error(self):
        reader = MagicMock()
        queries = MagicMock()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch(
                "umlsl_edit.commands.persistence.save_as_traffic_snapshot.PersistenceService.serialize",
                autospec=True,
            ) as serialize:
                serialize.side_effect = ValueError("bad payload")

                cmd = SaveAsTrafficSnapshot(file_path=tmp_path, traffic_snapshot_reader=reader, umlsl_queries=queries)
                with self.assertRaises(CommandValidationError):
                    cmd.execute()
        finally:
            os.remove(tmp_path)


class TestLoadTrafficSnapshot(unittest.TestCase):
    def test_execute_requires_file_path(self):
        cmd = LoadTrafficSnapshot(file_path="", application_controller=MagicMock())
        with self.assertRaises(CommandValidationError):
            cmd.execute()

    def test_execute_raises_on_missing_file(self):
        controller = MagicMock()
        cmd = LoadTrafficSnapshot(file_path="missing.json", application_controller=controller)
        with self.assertRaises(CommandValidationError):
            cmd.execute()

    def test_execute_raises_on_invalid_json(self):
        controller = MagicMock()
        controller.get_settings_model.return_value = MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
            tmp.write("{invalid json")
            tmp_path = tmp.name

        try:
            cmd = LoadTrafficSnapshot(file_path=tmp_path, application_controller=controller)
            with self.assertRaises(CommandValidationError):
                cmd.execute()
        finally:
            os.remove(tmp_path)

    def test_execute_deserializes_and_replaces_snapshot(self):
        controller = MagicMock()
        controller.get_settings_model.return_value = MagicMock()

        payload = {"meta": {"version": 1}, "roads": [], "cars": [], "queries": []}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
            json.dump(payload, tmp)
            tmp_path = tmp.name

        try:
            with patch(
                "umlsl_edit.commands.persistence.load_traffic_snapshot.PersistenceService.deserialize",
                autospec=True,
            ) as deserialize:
                cmd = LoadTrafficSnapshot(file_path=tmp_path, application_controller=controller)
                cmd.execute()

                self.assertTrue(deserialize.called)
                controller.replace_snapshot.assert_called_once()
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
