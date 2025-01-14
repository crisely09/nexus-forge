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

from enum import Enum, auto


class ResolvingStrategy(Enum):
    # POLICY Return all results, exact or fuzzy matches.
    ALL_MATCHES = auto()
    # POLICY Return a unique result, the closest match.
    BEST_MATCH = auto()
    # POLICY Return a unique result, the case-insensitive exact match.
    EXACT_CASEINSENSITIVE_MATCH = auto()
    # POLICY Return a unique result, the exact match.
    EXACT_MATCH = auto()
