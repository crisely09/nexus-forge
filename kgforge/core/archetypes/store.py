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
import json

import re
import time
from pyld import jsonld
from abc import ABC, abstractmethod
from rdflib import Graph
from pathlib import Path
from typing import Any, Callable, Dict, List, Match, Optional, Tuple, Union

from kgforge.core import Resource
from kgforge.core.commons.attributes import repr_class
from kgforge.specializations.mappers import DictionaryMapper
from kgforge.core.commons.context import Context
from kgforge.core.commons.exceptions import (
    DeprecationError,
    DownloadingError,
    FreezingError,
    RegistrationError,
    TaggingError,
    UpdatingError,
    UploadingError,
    QueryingError,
)
from kgforge.core.commons.execution import not_supported, run
from kgforge.core.conversions.rdf import from_jsonld
from kgforge.core.reshaping import collect_values


# NB: Do not 'from kgforge.core.archetypes import Resolver' to avoid cyclic dependency.

# FIXME: need to find a comprehensive way (different than list) to get all SPARQL reserved clauses
from kgforge.core.wrappings.dict import DictWrapper

DEFAULT_LIMIT = 100
DEFAULT_OFFSET = 0
SPARQL_CLAUSES = [
    "where",
    "filter",
    "select",
    "union",
    "limit",
    "construct",
    "optional",
    "bind",
    "values",
    "offset",
    "order by",
    "prefix",
    "graph",
    "distinct",
    "in",
    "as",
    "base",
    "prefix",
    "reduced",
    "describe",
    "ask",
    "named",
    "asc",
    "desc",
    "from",
    "optional",
    "graph",
    "regex",
    "union",
    "str",
    "lang",
    "langmatches",
    "datatype",
    "bound",
    "sameTerm",
    "isIRI",
    "isURI",
    "isBLANK",
    "isLITERAL",
    "group",
    "by",
    "order",
    "minus",
    "not",
    "exists"
]


class Store(ABC):

    # See demo_store.py in kgforge/specializations/stores/ for a reference implementation.

    # POLICY Methods of archetypes, except __init__, should not have optional arguments.

    # POLICY Implementations should be declared in kgforge/specializations/stores/__init__.py.
    # POLICY Implementations should not add methods but private functions in the file.
    # TODO Move from BDD to classical testing to have a more parameterizable test suite. DKE-135.
    # POLICY Implementations should pass tests/specializations/stores/demo_store.feature tests.

    def __init__(
        self,
        endpoint: Optional[str] = None,
        bucket: Optional[str] = None,
        token: Optional[str] = None,
        versioned_id_template: Optional[str] = None,
        file_resource_mapping: Optional[str] = None,
        model_context: Optional[Context] = None,
        searchendpoints: Optional[Dict] = None,
        **store_config,
    ) -> None:
        # file_resource_mapping: Optional[Union[Hjson, FilePath, URL]].
        # POLICY There could be data caching but it should be aware of changes made in the source.
        self.endpoint: Optional[str] = endpoint
        self.bucket: Optional[str] = bucket
        self.token: Optional[str] = token
        self.versioned_id_template: Optional[str] = versioned_id_template
        loaded = (
            self.mapping.load(file_resource_mapping) if file_resource_mapping else None
        )
        self.file_mapping: Optional[Any] = loaded
        self.model_context: Optional[Context] = model_context
        self.service: Any = self._initialize_service(
            self.endpoint, self.bucket, self.token, searchendpoints, **store_config
        )
        self.context: Context = (
            self.service.context if hasattr(self.service, "context") else None
        )
        self.metadata_context: Context = (
            self.service.metadata_context
            if hasattr(self.service, "metadata_context")
            else None
        )

    def __repr__(self) -> str:
        return repr_class(self)

    @property
    def mapping(self) -> Optional[Callable]:
        """Mapping class to load file_resource_mapping."""
        return None

    @property
    def mapper(self) -> Optional[Callable]:
        """Mapper class to map file metadata to a Resource with file_resource_mapping."""
        return None
    
    # [C]RUD.

    def register(
        self, data: Union[Resource, List[Resource]], schema_id: str = None
    ) -> None:
        # Replace None by self._register_many to switch to optimized bulk registration.
        run(
            self._register_one,
            None,
            data,
            required_synchronized=False,
            execute_actions=True,
            exception=RegistrationError,
            monitored_status="_synchronized",
            schema_id=schema_id,
        )

    def _register_many(self, resources: List[Resource], schema_id: str) -> None:
        # Bulk registration could be optimized by overriding this method in the specialization.
        # POLICY Should reproduce self._register_one() and execution._run_one() behaviours.
        not_supported()

    @abstractmethod
    def _register_one(self, resource: Resource, schema_id: str) -> None:
        # POLICY Should notify of failures with exception RegistrationError including a message.
        # POLICY Resource _store_metadata should be set using wrappers.dict.wrap_dict().
        # TODO This operation might be abstracted here when other stores will be implemented.
        pass

    # This expected that '@catch' is not used here. This is for actions.execute_lazy_actions().
    def upload(self, path: str, content_type: str, forge: Optional['KnowledgeGraphForge']) -> Union[Resource, List[Resource]]:
        # path: Union[FilePath, DirPath].
        if self.file_mapping is not None:
            p = Path(path)
            uploaded = self._upload(p, content_type)
            return self.mapper(forge).map(uploaded, self.file_mapping, None)
        else:
            raise UploadingError("no file_resource_mapping has been configured")

    def _upload(self, path: Path, content_type: str) -> Union[Any, List[Any]]:
        # path: Union[FilePath, DirPath].
        if path.is_dir():
            filepaths = [
                x for x in path.iterdir() if x.is_file() and not x.name.startswith(".")
            ]
            return self._upload_many(filepaths, content_type)
        else:
            return self._upload_one(path, content_type)

    def _upload_many(self, paths: List[Path], content_type: str) -> List[Any]:
        # Bulk uploading could be optimized by overriding this method in the specialization.
        # POLICY Should follow self._upload_one() policies.
        return [self._upload_one(x, content_type) for x in paths]

    def _upload_one(self, path: Path, content_type: str) -> Any:
        # path: FilePath.
        # POLICY Should notify of failures with exception UploadingError including a message.
        not_supported()

    # C[R]UD.

    @abstractmethod
    def retrieve(
        self, id: str, version: Optional[Union[int, str]], cross_bucket: bool, **params
    ) -> Resource:
        # POLICY Should notify of failures with exception RetrievalError including a message.
        # POLICY Resource _store_metadata should be set using wrappers.dict.wrap_dict().
        # POLICY Resource _synchronized should be set to True.
        # TODO These two operations might be abstracted here when other stores will be implemented.
        pass

    def _retrieve_filename(self, id: str) -> Tuple[str, str]:
        # TODO This operation might be adapted if other file metadata are needed.
        not_supported()
    
    def _prepare_download_one(self,
        url: str,
        store_metadata: Optional[DictWrapper],
        cross_bucket: bool
    ) -> Tuple[str, str]:
        # Prepare download url and download bucket
        not_supported()

    def download(
        self,
        data: Union[Resource, List[Resource]],
        follow: str,
        path: str,
        overwrite: bool,
        cross_bucket: bool,
        content_type: str = None
    ) -> None:
        # path: DirPath.
        urls = []
        store_metadata = []
        to_download = [data] if isinstance(data, Resource) else data
        for d in to_download:
            collected_values = collect_values(d, follow, DownloadingError)
            urls.extend(collected_values)
            store_metadata.extend(
                [d._store_metadata for _ in range(len(collected_values))]
            )
        if len(urls) == 0:
            raise DownloadingError(
                f"path to follow '{follow}' was not found in any provided resource."
            )
        dirpath = Path(path)
        dirpath.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        filepaths = []
        buckets = []
        download_urls = []
        download_store_metadata = []
        for i, x in enumerate(urls):
            x_download_url, x_bucket = self._prepare_download_one(x, store_metadata[i], cross_bucket)
            filename, store_content_type = self._retrieve_filename(x_download_url)
            if not content_type or (content_type and store_content_type == content_type):
                filepath = dirpath / filename
                if not overwrite and filepath.exists():
                    filepaths.append(f"{filepath}.{timestamp}")
                else:
                    filepaths.append(str(filepath))
                download_urls.append(x_download_url)
                buckets.append(x_bucket)
                download_store_metadata.append(store_metadata[i])
        if len(download_urls) > 1:
            self._download_many(download_urls, filepaths, download_store_metadata, cross_bucket, content_type, buckets)
        elif len(download_urls) == 1 :
            self._download_one(download_urls[0], filepaths[0], download_store_metadata[0], cross_bucket, content_type, buckets[0])
        else:
            raise DownloadingError(
                f"No resource with content_type {content_type} was found when following the resource path '{follow}'."
            )

    def _download_many(
        self,
        urls: List[str],
        paths: List[str],
        store_metadata: Optional[List[DictWrapper]],
        cross_bucket: bool,
        content_type: str,
        buckets: List[str]
    ) -> None:
        # paths: List[FilePath].
        # Bulk downloading could be optimized by overriding this method in the specialization.
        # POLICY Should follow self._download_one() policies.
        for url, path, store_m in zip(urls, paths, store_metadata):
            self._download_one(url, path, store_m, cross_bucket, content_type)

    def _download_one(
        self,
        url: str,
        path: str,
        store_metadata: Optional[DictWrapper],
        cross_bucket: bool,
        content_type: str,
        bucket: str
    ) -> None:
        # path: FilePath.
        # POLICY Should notify of failures with exception DownloadingError including a message.
        not_supported()

    # CR[U]D.

    def update(
        self, data: Union[Resource, List[Resource]], schema_id: Optional[str]
    ) -> None:
        # Replace None by self._update_many to switch to optimized bulk update.
        run(
            self._update_one,
            None,
            data,
            id_required=True,
            required_synchronized=False,
            execute_actions=True,
            exception=UpdatingError,
            monitored_status="_synchronized",
            schema_id=schema_id,
        )

    def _update_many(self, resources: List[Resource], schema_id: Optional[str]) -> None:
        # Bulk update could be optimized by overriding this method in the specialization.
        # POLICY Should reproduce self._update_one() and execution._run_one() behaviours.
        not_supported()

    @abstractmethod
    def _update_one(self, resource: Resource, schema_id: Optional[str]) -> None:
        # POLICY Should notify of failures with exception UpdatingError including a message.
        # POLICY Resource _store_metadata should be set using wrappers.dict.wrap_dict().
        # TODO This operation might be abstracted here when other stores will be implemented.
        pass

    def tag(self, data: Union[Resource, List[Resource]], value: str) -> None:
        # Replace None by self._tag_many to switch to optimized bulk tagging.
        # POLICY If tagging modify the resource, run() should have status='_synchronized'.
        run(
            self._tag_one,
            None,
            data,
            id_required=True,
            required_synchronized=True,
            exception=TaggingError,
            value=value,
        )

    def _tag_many(self, resources: List[Resource], value: str) -> None:
        # Bulk tagging could be optimized by overriding this method in the specialization.
        # POLICY Should reproduce self._tag_one() and execution._run_one() behaviours.
        # POLICY If tagging modify the resource, it should be done with status='_synchronized'.
        not_supported()

    def _tag_one(self, resource: Resource, value: str) -> None:
        # POLICY Should notify of failures with exception TaggingError including a message.
        # POLICY If tagging modify the resource, _store_metadata should be updated.
        not_supported()

    # CRU[D].

    def deprecate(self, data: Union[Resource, List[Resource]]) -> None:
        # Replace None by self._deprecate_many to switch to optimized bulk deprecation.
        run(
            self._deprecate_one,
            None,
            data,
            id_required=True,
            required_synchronized=True,
            exception=DeprecationError,
            monitored_status="_synchronized",
        )

    def _deprecate_many(self, resources: List[Resource]) -> None:
        # Bulk deprecation could be optimized by overriding this method in the specialization.
        # POLICY Should reproduce self._deprecate_one() and execution._run_one() behaviours.
        not_supported()

    def _deprecate_one(self, resource: Resource) -> None:
        # POLICY Should notify of failures with exception DeprecationError including a message.
        # POLICY Resource _store_metadata should be set using wrappers.dict.wrap_dict().
        # TODO This operation might be abstracted here when other stores will be implemented.
        not_supported()

    # Querying.

    def search(
        self, resolvers: Optional[List["Resolver"]], *filters, **params
    ) -> List[Resource]:

        # Positional arguments in 'filters' are instances of type Filter from wrappings/paths.py
        # A dictionary can be provided for filters:
        #  - {'key1': 'val', 'key2': {'key3': 'val'}} will be translated to
        #  - [Filter(operator='__eq__', path=['key1'], value='val'), Filter(operator='__eq__', path=['key2', 'key3'], value='val')]
        # Keyword arguments in 'params' could be:
        #   - debug: bool,
        #   - limit: int,
        #   - offset: int,
        #   - deprecated: bool,
        #   - resolving: str, with values in ('exact', 'fuzzy'),
        #   - lookup: str, with values in ('current', 'children').
        # POLICY Should use sparql() when 'sparql' is chosen as value  for the param 'search_endpoint'.
        # POLICY Should use elastic() when 'elastic' is chosen as value  for the param 'search_endpoint'.
        # POLICY Given parameters for limit and offset override the input query.
        # POLICY Should notify of failures with exception QueryingError including a message.
        # POLICY Resource _store_metadata should be set using wrappers.dict.wrap_dict().
        # POLICY Resource _synchronized should be set to True.
        # TODO These two operations might be abstracted here when other stores will be implemented.
        not_supported()

    def sparql(
        self, query: str, debug: bool, limit: int = DEFAULT_LIMIT, offset: int = DEFAULT_OFFSET, **params
    ) -> List[Resource]:
        rewrite = params.get("rewrite", True)
        qr = (
            rewrite_sparql(query, self.model_context, self.service.metadata_context)
            if self.model_context is not None and rewrite
            else query
        )
        if limit:
            qr = _replace_in_sparql(qr, "LIMIT", limit, DEFAULT_LIMIT, r" LIMIT \d+")
        if offset:
            qr = _replace_in_sparql(qr, "OFFSET", offset, DEFAULT_OFFSET, r" OFFSET \d+")
        if debug:
            self._debug_query(qr)
        return self._sparql(qr)

    def _sparql(self, query: str) -> List[Resource]:
        # POLICY Should notify of failures with exception QueryingError including a message.
        # POLICY Resource _store_metadata should not be set (default is None).
        # POLICY Resource _synchronized should not be set (default is False).
        not_supported()

    def elastic(
        self, query: str, debug: bool, limit: int = DEFAULT_LIMIT, offset: int = DEFAULT_OFFSET
    ) -> List[Resource]:
        query_dict = json.loads(query)
        if limit:
            query_dict["size"] = limit
        if offset:
            query_dict["from"] = offset 
        if debug:
            self._debug_query(query_dict)
        return self._elastic(json.dumps(query_dict))

    def _elastic(self, query: str) -> List[Resource]:
        # POLICY Should notify of failures with exception QueryingError including a message.
        # POLICY Resource _store_metadata should not be set (default is None).
        # POLICY Resource _synchronized should not be set (default is False).
        not_supported()

    # Versioning.

    def freeze(self, data: Union[Resource, List[Resource]]) -> None:
        # Replace None by self._freeze_many to switch to optimized bulk freezing.
        run(
            self._freeze_one,
            None,
            data,
            id_required=True,
            required_synchronized=True,
            exception=FreezingError,
        )

    def _freeze_many(self, resources: List[Resource]) -> None:
        # Bulk freezing could be optimized by overriding this method in the specialization.
        # POLICY Should reproduce self._freeze_one() and execution._run_one() behaviours.
        not_supported()

    def _freeze_one(self, resource: Resource) -> None:
        # Notify of failures with exception FreezingError including a message.
        # Use self.versioned_id_template.format(x=resource) to freeze IDs.
        for _, v in resource.__dict__.items():
            if isinstance(v, List):
                for x in v:
                    if isinstance(x, Resource):
                        self._freeze_one(x)
            elif isinstance(v, Resource):
                self._freeze_one(v)
        if hasattr(resource, "id"):
            resource.id = self.versioned_id_template.format(x=resource)

    # Utils.

    @abstractmethod
    def _initialize_service(
        self,
        endpoint: Optional[str],
        bucket: Optional[str],
        token: Optional[str],
        searchendpoints: Optional[Dict] = None,
        **store_config,
    ) -> Any:
        # POLICY Should initialize the access to the store according to its configuration.
        pass

    @staticmethod
    def _debug_query(query):
        if isinstance(query, Dict):
            print("Submitted query:", query)
        else:
            print(*["Submitted query:", *query.splitlines()], sep="\n   ")
        print()
    
    def rewrite_uri(self, uri: str, context: Context, **kwargs) -> str:
        """Rewrite a given uri using the store Context
        :param uri: a URI to rewrite.
        :param context: a Store Context object
        :return: str
        """
        pass


def _replace_in_sparql(qr, what, value, default_value, search_regex, replace_if_in_query=True):

    is_what_in_query = bool(re.search(f"{search_regex}", qr, flags=re.IGNORECASE))
    if is_what_in_query and value and not replace_if_in_query:
        raise QueryingError(f"Value for '{what}' is present in the provided query and set as argument: set 'replace_if_in_query' to True to replace '{what}' when present in the query.")
    replace_value = f" {what} {value}" if value else (f" {what} {default_value}" if default_value else None)
    if is_what_in_query and replace_if_in_query and replace_value:
        qr = re.sub(f"{search_regex}", replace_value, qr, flags=re.IGNORECASE)
    if not is_what_in_query and replace_value:
        qr = f"{qr} {replace_value}"
    return qr


def rewrite_sparql(query: str, context: Context, metadata_context) -> str:
    """Rewrite local property and type names from Model.template() as IRIs.

    Local names are mapped to IRIs by using a JSON-LD context, i.e. { "@context": { ... }} from a kgforge.core.commons.Context.
    In the case of contexts using prefixed names, prefixes are added to the SPARQL query prologue.
    In the case of non available contexts and vocab then the query is returned unchanged.
    """
    ctx = {}
    if metadata_context and metadata_context.document:
        ctx.update({
            k: v["@id"] if isinstance(v, Dict) and "@id" in v else v
            for k, v in metadata_context.document["@context"].items()
        })
    ctx.update({
        k: v["@id"] if isinstance(v, Dict) and "@id" in v else v
        for k, v in context.document["@context"].items()
    })
    prefixes = context.prefixes
    has_prefixes = prefixes is not None and len(prefixes.keys()) > 0
    if ctx.get("type") == "@type":
        if "rdf" in prefixes:
            ctx["type"] = "rdf:type"
        else:
            ctx["type"] = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

    def replace(match: Match) -> str:
        m4 = match.group(4)
        if m4 is None:
            return match.group(0)
        else:
            v = (
                ctx.get(m4, ":" + m4 if context.has_vocab() else None)
                if str(m4).lower() not in SPARQL_CLAUSES
                and not str(m4).startswith("https")
                else m4
            )
            if v is None:
                raise QueryingError(
                    f"Failed to construct a valid SPARQL query: add '{m4}'"
                    f", define an @vocab in the configured JSON-LD context or provide a fully correct SPARQL query."
                )
            m5 = match.group(5)
            if "//" in v:
                return f"<{v}>{m5}"
            else:
                return f"{v}{m5}"

    g4 = r"([a-zA-Z_]+)"
    g5 = r"([.;]?)"
    g0 = rf"((?<=[\s,[(/|!^])((a|true|false)|{g4}){g5}(?=[\s,\])/|?*+]))"
    g6 = r"(('[^']+')|('''[^\n\r]+''')|(\"[^\"]+\")|(\"\"\"[^\n\r]+\"\"\"))"
    rx = rf"{g0}|{g6}|(?<=< )(.*)(?= >)"
    qr = re.sub(rx, replace, query, flags=re.VERBOSE | re.MULTILINE)

    if not has_prefixes or "prefix" in str(qr).lower():
        return qr
    else:
        pfx = "\n".join(f"PREFIX {k}: <{v}>" for k, v in prefixes.items())
    if context.has_vocab():
        pfx = "\n".join([pfx, f"PREFIX : <{context.vocab}>"])
    return f"{pfx}\n{qr}"


def resources_from_construct_query(data, context):
    subject_triples = {}
    for r in data["results"]["bindings"]:
        subject = r["subject"]["value"]
        s = f"<{r['subject']['value']}>"
        p = f"<{r['predicate']['value']}>"
        if r["object"]["type"] == "uri":
            o = f"<{r['object']['value']}>"
        else:
            if "datatype" in r["object"]:
                o = f"\"{r['object']['value']}\"^^{r['object']['datatype']}"
            else:
                o = f"\"{r['object']['value']}\""
        if subject in subject_triples:
            subject_triples[subject] += f"\n{s} {p} {o} . "
        else:
            subject_triples[subject] = f"{s} {p} {o} . "

    def triples_to_resource(iri, triples):
        graph = Graph().parse(data=triples, format="nt")
        data_expanded = json.loads(graph.serialize(format="json-ld"))
        data_expanded = json.loads(graph.serialize(format="json-ld"))
        frame = {"@id": iri}
        data_framed = jsonld.frame(data_expanded, frame)
        compacted = jsonld.compact(data_framed, context.document)
        resource = from_jsonld(compacted)
        resource.context = (
            context.iri
            if context.is_http_iri()
            else context.document["@context"]
        )
        return resource

    return [triples_to_resource(s, t) for s, t in subject_triples.items()]