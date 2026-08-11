"""Interface for handling view events from the event controller."""
from abc import abstractmethod
from typing import Any

from PySide6.QtCore import QObject, SignalInstance

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.entities.road import Road
from umlsl_edit.model.entities.umlsl_query import UMLSLQuery


class ViewEventHandler(QObject):
    """
    Abstract interface for handling model change events in the view layer.

    This interface defines all methods that the view must implement to respond
    to changes in the model (TrafficSnapshot, Settings, UMLSLQueries).
    The EventController will call these methods when it receives events from the observable models.
    """

    # Car-related events
    @abstractmethod
    def add_car_view(self, car: Car) -> None:
        """
        Handle the addition of a car to the traffic snapshot.

        Args:
            car: The car entity that was added.
        """
        pass

    @abstractmethod
    def remove_car_view(self, car: Car) -> None:
        """
        Handle the removal of a car from the traffic snapshot.

        Args:
            car: The car entity that was removed.
        """
        pass

    @abstractmethod
    def update_car_view(self, car: Car) -> None:
        """
        Handle the update of a car in the traffic snapshot.

        Args:
            car: The car entity that was updated.
        """
        pass

    # Road-related events
    @abstractmethod
    def add_road_view(self, road: Road) -> None:
        """
        Handle the addition of a road to the traffic snapshot.

        Args:
            road: The road entity that was added.
        """
        pass

    @abstractmethod
    def remove_road_view(self, road: Road) -> None:
        """
        Handle the removal of a road from the traffic snapshot.

        Args:
            road: The road entity that was removed.
        """
        pass

    @abstractmethod
    def update_road_view(self, road: Road) -> None:
        """
        Handle the update of a road in the traffic snapshot.

        Args:
            road: The road entity that was updated.
        """
        pass

    # UMLSL Query-related events
    @abstractmethod
    def add_query_view(self, query: UMLSLQuery) -> None:
        """
        Handle the addition of a UMLSL query.

        Args:
            query: The UMLSL query that was added.
        """
        pass

    @abstractmethod
    def remove_query_view(self, query: UMLSLQuery) -> None:
        """
        Handle the removal of a UMLSL query.

        Args:
            query: The UMLSL query that was removed.
        """
        pass

    @abstractmethod
    def update_query_view(self, query: UMLSLQuery) -> None:
        """
        Handle the update of a UMLSL query.

        Args:
            query: The UMLSL query that was updated.
        """
        pass

    @abstractmethod
    def loading_query_view(self, query: UMLSLQuery) -> None:
        """
        Handle the loading of a UMLSL query (e.g., when a snapshot is reloaded).

        Args:
            query: The UMLSL query that is being loaded.
        """
        pass

    @abstractmethod
    def revalidation_started(self) -> None:
        pass

    @abstractmethod
    def revalidation_finished(self) -> None:
        pass

    @abstractmethod
    def on_snapshot_reloaded(self, snapshot: Any, queries: Any) -> None:
        """
        Handle a bulk snapshot reload event.

        Args:
            snapshot: The new traffic snapshot model.
            queries: The new UMLSL queries model.
        """
        pass

    @abstractmethod
    def set_coordinate_system(self, render_coordinate_system: bool) -> None:
        """
        Handle the toggle of coordinate system rendering.

        Args:
            render_coordinate_system: Whether to render the coordinate system.
        """
        pass

    @abstractmethod
    def set_grid(self, render_grid: bool) -> None:
        """
        Handle the toggle of the background grid.

        Args:
            render_grid: Whether to render the grid.
        """
        pass

    @abstractmethod
    def set_safety_distance(self, render_safety_distance: bool) -> None:
        """
        Handle the toggle of safety distance rendering.

        Args:
            render_safety_distance: Whether to render safety distances.
        """
        pass

    @abstractmethod
    def get_on_selection_changed_signal(self) -> "SignalInstance":
        """
        Returns a signal that is emitted when an entity is selected.
        The signal should carry the UID of the selected entity as a string.
        """
        pass

    @abstractmethod
    def get_on_snapshot_changed_signal(self) -> "SignalInstance":
        """
        Returns a signal that is emitted when the snapshot dirty state changes.
        The signal should carry a boolean indicating whether the snapshot has unsaved changes.
        """
        pass

    @abstractmethod
    def get_on_toggle_coordinate_system_signal(self) -> "SignalInstance":
        """
        Returns a signal that is emitted when the coordinate system rendering is toggled.
        The signal should carry a boolean indicating whether to render the coordinate system.
        """
        pass

    @abstractmethod
    def get_on_toggle_grid_signal(self) -> "SignalInstance":
        """
        Returns a signal that is emitted when the background grid rendering is toggled.
        The signal should carry a boolean indicating whether to render the grid.
        """
        pass

    @abstractmethod
    def get_on_toggle_safety_distance_signal(self) -> "SignalInstance":
        """
        Returns a signal that is emitted when the safety distance rendering is toggled.
        The signal should carry a boolean indicating whether to render safety distances.
        """
        pass

    @abstractmethod
    def get_on_show_snackbar_message_signal(self) -> "SignalInstance":
        """
        Returns a signal that is emitted when a transient status message should be shown.
        The signal should carry the message text and the display duration in milliseconds.
        """
        pass

    @abstractmethod
    def get_current_selected_uid(self) -> str:
        """
        Returns the UID of the currently selected entity.
        """
        pass

    @abstractmethod
    def entity_selected_view(self, uid: str) -> None:
        """
        Handle the selection of an entity.

        Args:
            uid: The uid of entity that was selected.
        """
        pass
