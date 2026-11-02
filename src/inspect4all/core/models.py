from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParamDoc:
    description: str | None
    type: str | None


@dataclass
class ReturnDoc:
    description: str | None
    type: str | None


@dataclass
class ExceptionDoc:
    type: str
    description: str | None


@dataclass
class Enrichment:
    source: str
    timestamp: str
    model: str
    content: dict
    confidence: float | None


@dataclass
class Documentation:
    short_description: str | None
    long_description: str | None
    full_text: str | None
    params: dict[str, ParamDoc]
    returns: ReturnDoc | None
    raises: list[ExceptionDoc]
    tags: dict[str, str]
    enrichments: list[Enrichment] | None = None


@dataclass
class ParameterInfo:
    name: str
    type: str | None
    default: str | None
    is_optional: bool
    annotations: list[str]


@dataclass
class FunctionInfo:
    name: str
    qualified_name: str
    documentation: Documentation | None
    source_code: str | None
    parameters: list[ParameterInfo]
    return_type: str | None
    modifiers: list[str]
    annotations: list[str]
    calls: list[str]
    line_range: tuple[int, int]
    is_constructor: bool
    nested_functions: list[FunctionInfo]
    language_specific: dict


@dataclass
class FieldInfo:
    name: str
    type: str | None
    modifiers: list[str]
    default_value: str | None
    annotations: list[str]


@dataclass
class TypeInfo:
    kind: str  # "class"|"struct"|"interface"|"enum"|"trait"
    name: str
    qualified_name: str
    documentation: Documentation | None
    source_code: str | None
    base_classes: list[str]
    interfaces: list[str]
    modifiers: list[str]
    annotations: list[str]
    fields: list[FieldInfo]
    methods: list[FunctionInfo]
    line_range: tuple[int, int]
    language_specific: dict


@dataclass
class ImportInfo:
    module: str
    name: str
    alias: str | None
    is_internal: bool
    kind: str  # "module"|"function"|"class"|"static_member"|"wildcard"


@dataclass
class FileInfo:
    path: str
    name: str
    extension: str
    language: str
    package: str | None
    documentation: Documentation | None
    is_test: bool


@dataclass
class MainInfo:
    has_main: bool
    main_function: str | None
    type: str | None  # "script"|"application"


@dataclass
class FileAnalysis:
    file: FileInfo
    imports: list[ImportInfo]
    types: list[TypeInfo]
    functions: list[FunctionInfo]
    main_info: MainInfo | None
    language_specific: dict

    def all_functions(self) -> list[FunctionInfo]:
        """All functions in the file, with nested functions flattened."""
        result: list[FunctionInfo] = []

        def _walk(funcs: list[FunctionInfo]) -> None:
            for f in funcs:
                result.append(f)
                _walk(f.nested_functions)

        _walk(self.functions)
        for t in self.types:
            _walk(t.methods)
        return result


@dataclass
class Dependency:
    name: str
    version: str | None
    source: str
    language: str
    scope: str  # "runtime"|"dev"|"test"|"compile"|"provided"
    build_tool: str | None


@dataclass
class LicenseMatch:
    type: str
    confidence: float


@dataclass
class LicenseInfo:
    detected: list[LicenseMatch]
    source_files: list[str]
    text: str | None


@dataclass
class ReadmeFile:
    path: str
    content: str


@dataclass
class FileTreeEntry:
    path: str
    language: str | None
    type: str  # "source"|"build"|"documentation"|"config"|"test"|"data"


@dataclass
class InvocationEntry:
    type: str
    run: str
    language: str
    entry_point: str | None
    has_main: bool
    mentioned_in_readme: bool
    ranking: int


@dataclass
class TestEntry:
    type: str
    run: str
    language: str
    files: list[str]


@dataclass
class RepositoryAnalysis:
    repo_path: str
    languages: dict[str, int]
    files: list[FileAnalysis]
    readme_files: list[ReadmeFile]
    directory_tree: list[FileTreeEntry]
    dependencies: list[Dependency]
    software_type: str
    software_invocation: list[InvocationEntry]
    tests: list[TestEntry]
    license: LicenseInfo
    metadata: dict
    call_graph: dict
    language_specific: dict = field(default_factory=dict)
