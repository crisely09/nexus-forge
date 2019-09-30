from typing import Optional, Union

from kgforge.core.commons.typing import ManagedData
from kgforge.core.resources import Resource, Resources


class QueryingInterface:

    def __init__(self, forge: "KnowledgeGraphForge") -> None:
        self.forge = forge

    def retrieve(self, id: str, version: Optional[Union[int, str]] = None) -> Resource:
        return self.forge._store.retrieve(id, version)

    def search(self, *filters, **params) -> Resources:
        revolvers = self.forge.ontologies
        return self.forge._store.search(revolvers, *filters, **params)

    def sparql(self, query: str) -> Resources:
        prefixes = self.forge.modeling.prefixes()
        return self.forge._store.sparql(prefixes, query)

    def download(self, data: ManagedData, follow: str, path: str) -> None:
        self.forge._store.download(data, follow, path)
