from typing import Any, Callable, List

from kgforge.core import Resource
from kgforge.core.commons.typing import ManagedData
from kgforge.core.transforming import Mapping


class TransformingInterface:

    def __init__(self, forge):
        self.forge = forge

    def map(self, data: Any, mapper: Callable, mapping: Mapping) -> ManagedData:
        return mapper(self.forge).map(data, mapping)

    def reshape(self, data: ManagedData, keep: List[str], versioned: bool = False) -> ManagedData:
        print("FIXME - TransformingInterface.reshape()")
        return Resource()
