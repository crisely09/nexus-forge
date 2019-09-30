from kgforge.core.commons.typing import ManagedData
from kgforge.core.storing.store import Store


class StoringInterface:

    def __init__(self, store: Store) -> None:
        self._store: Store = store

    def register(self, data: ManagedData) -> None:
        self._store.register(data, update=False)

    def update(self, data: ManagedData) -> None:
        self._store.update(data)

    def tag(self, data: ManagedData, value: str) -> None:
        self._store.tag(data, value)

    def deprecate(self, data: ManagedData) -> None:
        self._store.deprecate(data)
