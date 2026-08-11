"""
Road list model for the UMLSL Traffic Editor.

Provides a list model for displaying road entities in QML list views,
with support for selection highlighting and road property display.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QModelIndex, Qt

if TYPE_CHECKING:
    from umlsl_edit.controllers import ApplicationController

from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.view.ui.lists.models.entity_list_model import EntityModel


class RoadListModel(EntityModel):
    """
    List model for road entities displayed in the sidebar.

    Provides data roles for road name, orientation icon, and position value.
    Supports selection highlighting and edit dialog integration.

    Roles:
        NameRole: The road's display name.
        IconRole: Boolean indicating if the road icon should be rotated (vertical).
        ValueRole: Formatted string showing the road's position.

    Attributes:
        _application_controller: Reference to the application controller.
    """

    NameRole = EntityModel.NextRole
    IconRole = EntityModel.NextRole + 1
    ValueRole = EntityModel.NextRole + 2

    def __init__(
            self,
            application_controller: "ApplicationController",
            parent=None,
    ) -> None:
        """
        Initialize the road list model.

        Args:
            application_controller: The application controller for commands.
            parent: The parent QObject. Defaults to None.
        """
        super().__init__(parent=parent)
        self._application_controller = application_controller

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Return the number of roads in the model.

        Args:
            parent: The parent index (unused for flat lists).

        Returns:
            The number of road entities.
        """
        return len(self._data)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object | None:
        """
        Return the data for a specific row and role.

        Handles road-specific roles (name, icon, value) and delegates
        common roles to the parent class.

        Args:
            index: The model index to query.
            role: The data role to retrieve.

        Returns:
            The requested data, or None if invalid.
        """
        parent_result = super().data(index, role)
        if parent_result is not None:
            return parent_result

        if not index.isValid():
            return None

        road = self._data[index.row()]
        is_vertical = road.orientation == RoadOrientation.VERTICAL

        if role == RoadListModel.NameRole:
            return str(road.name)
        elif role == RoadListModel.IconRole:
            return bool(is_vertical)
        elif role == RoadListModel.ValueRole:
            axis_name = "x" if is_vertical else "y"
            return f"{axis_name} = {road.position}"

        return None

    def roleNames(self) -> dict[int, bytes]:
        """
        Return the mapping of role IDs to QML role names.

        Extends the parent class roles with road-specific roles.

        Returns:
            Dictionary mapping role constants to QML property names.
        """
        roles = super().roleNames()
        roles.update({
            RoadListModel.NameRole: b"role_name",
            RoadListModel.IconRole: b"role_isRotated",
            RoadListModel.ValueRole: b"role_value",
        })
        return roles
