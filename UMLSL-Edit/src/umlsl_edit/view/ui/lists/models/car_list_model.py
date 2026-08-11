"""
Car list model for the UMLSL Traffic Editor.

Provides a QAbstractListModel subclass for displaying car entities in QML list views.
Exposes car properties such as name, color, and lane assignment as model roles.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QModelIndex, Qt

from umlsl_edit.view.ui.lists.models.entity_list_model import EntityModel

if TYPE_CHECKING:
    from umlsl_edit.controllers import ApplicationController


class CarModel(EntityModel):
    """
    List model for car entities.

    Extends EntityModel to provide car-specific data roles for display in QML.
    Each car exposes its name, color, and current lane assignment as bindable
    properties.

    Roles:
        NameRole: The car's display name.
        ColorRole: The car's color as a hex string.
        ValueRole: A formatted string showing the car's road and lane assignment.

    Attributes:
        _application_controller: Reference to the application controller.
    """

    NameRole = EntityModel.NextRole
    ColorRole = EntityModel.NextRole + 1
    ValueRole = EntityModel.NextRole + 2

    def __init__(
            self,
            application_controller: "ApplicationController",
            parent=None,
    ) -> None:
        """
        Initialize the car list model.

        Args:
            application_controller: The application controller for accessing
                data and executing commands.
            parent: The parent QObject. Defaults to None.
        """
        super().__init__(parent)
        self._application_controller = application_controller

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Return the number of cars in the model.

        Args:
            parent: The parent index (unused for flat lists).

        Returns:
            The number of car entities.
        """
        return len(self._data)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        """
        Return data for a specific car and role.

        Args:
            index: The model index specifying the row.
            role: The data role to retrieve.

        Returns:
            The requested data, or None if the role is not handled.
        """
        parent_result = super().data(index, role)
        if parent_result is not None:
            return parent_result

        if not index.isValid():
            return None

        car = self._data[index.row()]

        if role == CarModel.NameRole:
            return str(car.name)
        elif role == CarModel.ColorRole:
            return str(car.color)
        elif role == CarModel.ValueRole:
            road = self._application_controller.data_controller.get_road_by_uid(car.lane.road_uid)
            road_name = road.name if road else "Unknown road"
            lane_name = car.lane.get_name(self._application_controller.get_traffic_snapshot_reader())
            return f"R: {road_name} L: {lane_name}"

        return None

    def roleNames(self) -> dict[int, bytes]:
        """
        Return the mapping of role IDs to QML property names.

        Returns:
            Dictionary mapping role integers to byte-string property names.
        """
        roles = super().roleNames()
        roles.update({
            CarModel.NameRole: b"role_name",
            CarModel.ColorRole: b"role_color",
            CarModel.ValueRole: b"role_value",
        })
        return roles
