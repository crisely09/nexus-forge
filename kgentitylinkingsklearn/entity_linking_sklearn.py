# 
# Blue Brain Nexus Forge is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Blue Brain Nexus Forge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with Blue Brain Nexus Forge. If not, see <https://choosealicense.com/licenses/lgpl-3.0/>.
from pathlib import Path
from typing import Any, Dict, List, Callable, Optional, Tuple

from kgentitylinkingsklearn import EntityLinkerServiceSkLearn
from kgforge.core.commons.actions import LazyAction
from kgforge.specializations.mappers import DictionaryMapper
from kgforge.specializations.mappings import DictionaryMapping
from kgforge.specializations.resolvers import EntityLinker


class EntityLinkerSkLearn(EntityLinker):

    def __init__(self, source: str, targets: List[Dict[str, Any]], result_resource_mapping: str,
                 **source_config) -> None:
        super().__init__(source, targets, result_resource_mapping, **source_config)

    @property
    def mapping(self) -> Callable:
        return DictionaryMapping

    @property
    def mapper(self) -> Callable:
        return DictionaryMapper

    @staticmethod
    def _service_from_directory(dirpath: Path, targets: Dict[str,  Dict[str, Dict[str, str]]], **source_config) -> Dict[str, LazyAction]:
        # FIXME: the same model is loaded multiple times if provided for multiple targets
        return {target: LazyAction(EntityLinkerServiceSkLearn.from_pretrained, dirpath, filename_filter["bucket"]) for target, filename_filter in
                targets.items()}

    def _is_target_valid(self, target: str) -> Optional[bool]:
        if target and self.service and target not in self.service:
            raise ValueError(f"Unknown target value: {target}. Supported targets are: {self.service.keys()}")
        else:
            return True
