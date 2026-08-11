from typing import TypeVar, MutableMapping, Iterator, MutableSequence, Callable, Any, KeysView, ValuesView, \
    ItemsView, Mapping
from enum import Enum

Key = TypeVar("Key")
Value = TypeVar("Value")
T = TypeVar("T")


class Observable:
    """
    Base class for observable objects using pure Python observer pattern.
    No dependency on PySide or any UI framework.
    """

    def __init__(self):
        self._observers: list[Callable] = []

    def attach(self, observer_callback: Callable) -> None:
        """Attach an observer callback."""
        if observer_callback not in self._observers:
            self._observers.append(observer_callback)

    def detach(self, observer_callback: Callable) -> None:
        """Detach an observer callback."""
        if observer_callback in self._observers:
            self._observers.remove(observer_callback)

    def notify(self, event_type: Enum, data=None) -> None:
        """Notify all observers of a change.

        Args:
            event_type: An Enum representing the type of event
            data: Optional data associated with the event
        """
        for observer in self._observers:
            observer(event_type, data)


class ObservableDict(MutableMapping[Key, Value]):
    """
    A dictionary that notifies via callbacks on additions, removals, and updates.
    Pure Python implementation without PySide dependencies.
    """
    def __init__(
            self,
            on_add: Callable[[Value], None] = None,
            on_remove: Callable[[Value], None] = None,
            on_update: Callable[[Value], None] = None,
            initial_data: dict[Key, Value] | None = None,
    ):
        """
        Initialize an ObservableDict.

        Args:
            on_add: Callback called when a new key-value pair is added (receives value)
            on_remove: Callback called when a key-value pair is removed (receives value)
            on_update: Callback called when an existing value is updated (receives new value)
            initial_data: Optional initial dictionary data
        """
        self._data: dict[Key, Value] = {}
        self._on_add = on_add
        self._on_remove = on_remove
        self._on_update = on_update

        if initial_data:
            for key, value in initial_data.items():
                self._data[key] = value

    def __setitem__(self, key: Key, value: Value) -> None:
        """Set an item, triggering on_add or on_update callback."""
        is_new = key not in self._data
        self._data[key] = value

        if is_new:
            if self._on_add:
                self._on_add(value)
        else:
            if self._on_update:
                self._on_update(value)

    def __delitem__(self, key: Key) -> None:
        """Delete an item, triggering on_remove callback."""
        value = self._data[key]
        del self._data[key]

        if self._on_remove:
            self._on_remove(value)

    def __getitem__(self, key: Key) -> Value:
        """Get an item by key."""
        return self._data[key]

    def __iter__(self) -> Iterator[Key]:
        """Iterate over keys."""
        return iter(self._data)

    def __len__(self) -> int:
        """Return the number of items."""
        return len(self._data)

    def __dict__(self) -> dict[Key, Value]:
        """Return the internal dictionary."""
        return self._data

    def __add__(self, other: object) -> "ObservableDict":
        """Combine two ObservableDicts into a new one."""
        if not isinstance(other, ObservableDict):
            return NotImplemented

        combined_data = {**self._data, **other._data}
        return ObservableDict(
            on_add=self._on_add,
            on_remove=self._on_remove,
            on_update=self._on_update,
            initial_data=combined_data
        )


class ObservableList(MutableSequence[T]):
    """
    A list that notifies via callbacks on additions, removals, and updates.
    """
    def __init__(
            self,
            on_add: Callable[[T], None] = None,
            on_remove: Callable[[T], None] = None,
            on_update: Callable[[T], None] = None,
            initial_data: list[T] | None = None,
    ):
        """
        Initialize an ObservableList.

        Args:
            on_add: Callback called when an item is added (receives item)
            on_remove: Callback called when an item is removed (receives item)
            on_update: Callback called when an item is updated (receives new item)
            initial_data: Optional initial list data
        """
        self._data: list[T] = []
        self._on_add = on_add
        self._on_remove = on_remove
        self._on_update = on_update

        if initial_data:
            self._data.extend(initial_data)

    def insert(self, index: int, value: T) -> None:
        """Insert an item at the given index, triggering on_add callback."""
        self._data.insert(index, value)

        if self._on_add:
            self._on_add(value)

    def __getitem__(self, index: int) -> T:
        """Get an item by index."""
        return self._data[index]

    def __setitem__(self, index: int, value: T) -> None:
        """Set an item at the given index, triggering on_update callback."""
        self._data[index] = value

        if self._on_update:
            self._on_update(value)

    def __delitem__(self, index: int) -> None:
        """Delete an item at the given index, triggering on_remove callback."""
        value = self._data[index]
        del self._data[index]

        if self._on_remove:
            self._on_remove(value)

    def __len__(self) -> int:
        """Return the number of items."""
        return len(self._data)

    def append(self, value: T) -> None:
        """Append an item to the end of the list, triggering on_add callback."""
        self._data.append(value)

        if self._on_add:
            self._on_add(value)





class ReadOnlyMergedDictView(Mapping[str, Any]):
    """
    A read-only view over multiple ObservableDicts, merged into a single Mapping.

    Later dictionaries in the list override earlier ones for duplicate keys.
    """

    def __init__(self, observable_dicts: list[ObservableDict]):
        """
        Initialize a read-only merged view.

        Args:
            observable_dicts: A list of ObservableDicts to merge in order
        """
        self._observable_dicts = observable_dicts

    def __getitem__(self, key: str) -> Any:
        """Get an item by key from the merged dicts."""
        for observable_dict in reversed(self._observable_dicts):
            if key in observable_dict:
                return observable_dict[key]
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys in the merged dicts."""
        return iter(self.keys())

    def __len__(self) -> int:
        """Return the number of unique items across merged dicts."""
        return len(self.keys())

    def __contains__(self, key: object) -> bool:
        """Check if key exists in any underlying dict."""
        return any(key in observable_dict for observable_dict in self._observable_dicts)

    def keys(self) -> KeysView[str]:
        """Return keys view of the merged dicts."""
        return self._merge_dicts().keys()

    def values(self) -> ValuesView[Any]:
        """Return values view of the merged dicts."""
        return self._merge_dicts().values()

    def items(self) -> ItemsView[str, Any]:
        """Return items view of the merged dicts."""
        return self._merge_dicts().items()

    def _merge_dicts(self) -> dict[str, Any]:
        """Merge all dicts into a single standard dict."""
        merged: dict[str, Any] = {}
        for observable_dict in self._observable_dicts:
            merged.update(observable_dict)
        return merged
