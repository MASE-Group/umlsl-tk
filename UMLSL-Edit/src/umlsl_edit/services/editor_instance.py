"""
Hand a snapshot from UMLSL-Sim to an UMLSL-Edit window that is already open.

UMLSL-Sim opens the editor with ``python -m umlsl_edit.main --import-from-sim
FILE``. That process first tries ``forward_to_running_editor``. If another
editor listens on the local socket, the process hands it the file and exits.
Otherwise it opens its own window and starts an ``EditorInstanceServer``, so
that the next snapshot from UMLSL-Sim goes to this window.

Plain launches of the editor are not affected: they still open a new window
each time, and the first window that starts listens for UMLSL-Sim.

The protocol is one JSON line from the client, ``{"import_from_sim": PATH}``,
answered with the line ``ok``.
"""
from __future__ import annotations

import getpass
import json
import re

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

IMPORT_FROM_SIM_FLAG = "--import-from-sim"
TIMEOUT_MS = 2000


def server_name() -> str:
    """The socket name, one per user, so that users on one machine do not mix.

    Kept short, because the socket's full path is limited to about 100
    characters and the temp folder already takes half of that on macOS.
    """
    try:
        user = getpass.getuser()
    except (KeyError, OSError):  # no user name in the environment
        user = "user"
    return "umlsl-edit-" + re.sub(r"[^A-Za-z0-9_]+", "_", user)[:24]


def import_request(argv: list[str]) -> str | None:
    """The file after ``--import-from-sim`` in ``argv``, or ``None``."""
    if IMPORT_FROM_SIM_FLAG in argv:
        index = argv.index(IMPORT_FROM_SIM_FLAG)
        if index + 1 < len(argv):
            return argv[index + 1]
    return None


def forward_to_running_editor(file_path: str, name: str | None = None) -> bool:
    """
    Ask an open editor to import ``file_path``.

    Returns:
        True if an editor took the file, False if none is listening.
    """
    socket = QLocalSocket()
    socket.connectToServer(name or server_name())
    if not socket.waitForConnected(TIMEOUT_MS):
        return False
    socket.write((json.dumps({"import_from_sim": file_path}) + "\n").encode("utf-8"))
    socket.waitForBytesWritten(TIMEOUT_MS)
    accepted = socket.waitForReadyRead(TIMEOUT_MS) and bytes(socket.readLine()).strip() == b"ok"
    socket.disconnectFromServer()
    return accepted


class EditorInstanceServer(QObject):
    """Listens for snapshots that UMLSL-Sim sends to this editor window."""

    import_requested = Signal(str)
    """A file to import, sent by UMLSL-Sim through ``forward_to_running_editor``."""

    def __init__(self, parent: QObject | None = None, name: str | None = None):
        super().__init__(parent)
        self._name = name or server_name()
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)

    def listen(self) -> bool:
        """
        Start listening, unless another editor already does.

        A socket file left behind by an editor that crashed is removed first.

        Returns:
            True if this editor now receives the snapshots from UMLSL-Sim.
        """
        if self._server.listen(self._name):
            return True
        probe = QLocalSocket()
        probe.connectToServer(self._name)
        if probe.waitForConnected(200):
            probe.disconnectFromServer()
            return False
        QLocalServer.removeServer(self._name)
        return self._server.listen(self._name)

    @property
    def is_listening(self) -> bool:
        return self._server.isListening()

    def close(self) -> None:
        self._server.close()

    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self._on_ready_read(s))
            socket.disconnected.connect(socket.deleteLater)

    def _on_ready_read(self, socket: QLocalSocket) -> None:
        if not socket.canReadLine():
            return
        try:
            message = json.loads(bytes(socket.readLine()).decode("utf-8"))
            file_path = str(message["import_from_sim"])
        except (ValueError, KeyError, TypeError):
            socket.disconnectFromServer()
            return
        # Answer first: handling the file may wait for the user in a dialog.
        socket.write(b"ok\n")
        socket.flush()
        self.import_requested.emit(file_path)
