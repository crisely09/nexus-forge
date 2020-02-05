#
# Knowledge Graph Forge is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Knowledge Graph Forge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Knowledge Graph Forge. If not, see <https://www.gnu.org/licenses/>.

# Test suite for functions on dictionaries.

import pytest

from kgforge.core.commons.dictionaries import with_defaults


@pytest.fixture
def original():
    return {
        "k1": "v1a",
        "k2": "v2a",
        "k3": "v3a",
        "k4": "v4a",
    }


@pytest.fixture
def other():
    return {
        "k2": "v2b",
        "k3": "v3b",
        "k4": "v4b",
    }


class TestWithDefaults:

    # Same.

    def test_same_missing_missing(self, original, other):
        # Same Store name. Missing endpoint. Missing token.
        # => Use other endpoint and other token.
        original["k2"] = "v2b"
        del original["k3"]
        del original["k4"]
        with_defaults(original, other, "k2", ["k3", "k4"])
        assert original["k3"] == "v3b"
        assert original["k4"] == "v4b"

    def test_same_given_missing(self, original, other):
        # Same Store name. Given endpoint. Missing token.
        # => Use other endpoint and other token.
        original["k2"] = "v2b"
        del original["k4"]
        with_defaults(original, other, "k2", ["k3", "k4"])
        assert original["k3"] == "v3b"
        assert original["k4"] == "v4b"

    def test_same_given_given(self, original, other):
        # Same Store name. Given endpoint. Given token.
        # => Use other endpoint and other token.
        original["k2"] = "v2b"
        with_defaults(original, other, "k2", ["k3", "k4"])
        assert original["k3"] == "v3b"
        assert original["k4"] == "v4b"

    # Different.

    def test_different_missing_missing(self, original, other):
        # Different Store name. Missing endpoint. Missing token.
        # => Use other endpoint and other token.
        del original["k3"]
        del original["k4"]
        with_defaults(original, other, "k2", ["k3", "k4"])
        assert original["k3"] == "v3b"
        assert original["k4"] == "v4b"

    def test_different_given_missing(self, original, other):
        # Different Store name. Given endpoint. Missing token.
        # => Use original endpoint and other token.
        del original["k4"]
        with_defaults(original, other, "k2", ["k3", "k4"])
        assert original["k3"] == "v3a"
        assert original["k4"] == "v4b"

    def test_different_given_given(self, original, other):
        # Different Store name. Given endpoint. Given token.
        # => Use original endpoint and original token.
        with_defaults(original, other, "k2", ["k3", "k4"])
        assert original["k3"] == "v3a"
        assert original["k4"] == "v4a"