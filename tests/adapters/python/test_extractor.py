import ast
from pathlib import Path

from inspect4all.adapters.python.extractor import PythonExtractor


def _make(source: str) -> PythonExtractor:
    tree = ast.parse(source)
    return PythonExtractor(
        tree=tree, source=source, file_path=Path("test.py"), module_name="test"
    )


def test_extract_top_level_function():
    src = 'def process(data: list, strict: bool = False) -> dict:\n    """Process."""\n    return {}'
    ext = _make(src)
    funcs = ext.extract_functions()
    assert len(funcs) == 1
    f = funcs[0]
    assert f.name == "process"
    assert f.return_type == "dict"
    assert len(f.parameters) == 2
    assert f.parameters[1].is_optional is True
    assert f.parameters[1].default == "False"


def test_extract_class_with_method():
    src = "class MyClass(Base):\n    def method(self, x: int) -> str:\n        return str(x)"
    ext = _make(src)
    types = ext.extract_types()
    assert len(types) == 1
    t = types[0]
    assert t.kind == "class"
    assert t.name == "MyClass"
    assert t.base_classes == ["Base"]
    assert len(t.methods) == 1
    assert t.methods[0].name == "method"


def test_extract_imports():
    src = "import os\nfrom typing import List\nfrom .utils import helper"
    ext = _make(src)
    imports = ext.extract_imports()
    assert len(imports) == 3
    modules = {i.module for i in imports}
    assert "os" in modules or any(i.name == "os" for i in imports)


def test_extract_calls_in_function():
    src = "def run():\n    result = clean(data)\n    os.path.join('a', 'b')"
    ext = _make(src)
    funcs = ext.extract_functions()
    assert "clean" in funcs[0].calls
    assert "os.path.join" in funcs[0].calls


def test_source_code_extracted():
    src = "def hello():\n    return 'world'"
    ext = _make(src)
    funcs = ext.extract_functions()
    assert "return 'world'" in funcs[0].source_code


def test_qualified_name_includes_module():
    src = "def greet(): pass"
    ext = _make(src)
    funcs = ext.extract_functions()
    assert funcs[0].qualified_name == "test.greet"


def test_class_qualified_name():
    src = "class Foo:\n    def bar(self): pass"
    ext = _make(src)
    types = ext.extract_types()
    assert types[0].qualified_name == "test.Foo"
    assert types[0].methods[0].qualified_name == "test.Foo.bar"


def test_nested_functions_extracted():
    src = (
        "def outer():\n"
        "    def inner(x):\n"
        "        def innermost():\n"
        "            pass\n"
        "        return x\n"
        "    return inner\n"
    )
    ext = _make(src)
    funcs = ext.extract_functions()
    assert len(funcs) == 1
    inner = funcs[0].nested_functions[0]
    assert inner.qualified_name == "test.outer.inner"
    assert (
        inner.nested_functions[0].qualified_name == "test.outer.inner.innermost"
    )
