import textwrap
from pathlib import Path

from inspect4all.adapters.java.extractor import JavaExtractor
from inspect4all.adapters.java.parser import JavaParser

LIBRARY_JAVA = textwrap.dedent("""\
    package com.example;

    import java.util.List;
    import java.util.ArrayList;

    /**
     * A calculator class.
     *
     * @author test
     */
    public class Calculator {
        private int value;

        /**
         * Constructs calculator with initial value.
         *
         * @param value initial value
         */
        public Calculator(int value) {
            this.value = value;
        }

        /**
         * Adds two numbers.
         *
         * @param a first number
         * @param b second number
         * @return sum of a and b
         */
        public int add(int a, int b) {
            return a + b;
        }

        public int getValue() {
            return this.value;
        }
    }
""")


def _make_extractor(java_src: str, tmp_path: Path) -> JavaExtractor:
    f = tmp_path / "Calculator.java"
    f.write_text(java_src, encoding="utf-8")
    pr = JavaParser().parse(f)
    return JavaExtractor(pr.tree, pr.source, f, "com.example")


def test_extract_types(tmp_path):
    ex = _make_extractor(LIBRARY_JAVA, tmp_path)
    types = ex.extract_types()
    assert len(types) == 1
    assert types[0].name == "Calculator"


def test_type_has_methods(tmp_path):
    ex = _make_extractor(LIBRARY_JAVA, tmp_path)
    types = ex.extract_types()
    calc = types[0]
    method_names = [m.name for m in calc.methods]
    assert "add" in method_names
    assert "getValue" in method_names


def test_constructor_is_flagged(tmp_path):
    ex = _make_extractor(LIBRARY_JAVA, tmp_path)
    types = ex.extract_types()
    ctors = [m for m in types[0].methods if m.is_constructor]
    assert len(ctors) == 1
    assert ctors[0].name == "Calculator"


def test_method_has_parameters(tmp_path):
    ex = _make_extractor(LIBRARY_JAVA, tmp_path)
    types = ex.extract_types()
    add_method = next(m for m in types[0].methods if m.name == "add")
    param_names = [p.name for p in add_method.parameters]
    assert "a" in param_names
    assert "b" in param_names


def test_method_has_source_code(tmp_path):
    ex = _make_extractor(LIBRARY_JAVA, tmp_path)
    types = ex.extract_types()
    add_method = next(m for m in types[0].methods if m.name == "add")
    assert add_method.source_code is not None
    assert "return a + b" in add_method.source_code


def test_extract_imports(tmp_path):
    ex = _make_extractor(LIBRARY_JAVA, tmp_path)
    imports = ex.extract_imports()
    names = [i.name for i in imports]
    assert "List" in names or "java.util.List" in names


def test_fields_in_type(tmp_path):
    ex = _make_extractor(LIBRARY_JAVA, tmp_path)
    types = ex.extract_types()
    field_names = [f.name for f in types[0].fields]
    assert "value" in field_names


CALLS_JAVA = textwrap.dedent("""\
    package com.example;

    public class Runner {
        public void run() {
            step();
            System.out.println("go");
            Helper h = new Helper();
            h.assist();
        }

        public void step() {
        }
    }
""")


def test_method_calls_extracted(tmp_path):
    f = tmp_path / "Runner.java"
    f.write_text(CALLS_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    run = next(
        m for t in ex.extract_types() for m in t.methods if m.name == "run"
    )
    assert "step" in run.calls
    assert "System.out.println" in run.calls
    assert "Helper" in run.calls  # constructor call
    assert "h.assist" in run.calls


# -- Generic type rendering ---------------------------------------------------

GENERICS_JAVA = textwrap.dedent("""\
    package com.example;

    import java.util.List;
    import java.util.Map;
    import java.util.Optional;

    public class GenericContainer {
        private List<String> names;
        private Map<String, Integer> scores;
        private Map<String, List<Integer>> nested;

        public List<String> getNames() {
            return names;
        }

        public Map<String, Integer> getScores() {
            return scores;
        }

        public Optional<String> findFirst() {
            return Optional.empty();
        }

        public void process(List<Integer> items) {
        }
    }
""")


def test_generic_field_type_rendered(tmp_path):
    """Fields with generic types should render as List<String>, not just List."""
    f = tmp_path / "GenericContainer.java"
    f.write_text(GENERICS_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    types = ex.extract_types()
    fields_by_name = {fld.name: fld for fld in types[0].fields}
    assert fields_by_name["names"].type == "List<String>"
    assert fields_by_name["scores"].type == "Map<String, Integer>"


def test_nested_generic_field_type_rendered(tmp_path):
    """Nested generics like Map<String, List<Integer>> should render fully."""
    f = tmp_path / "GenericContainer.java"
    f.write_text(GENERICS_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    types = ex.extract_types()
    fields_by_name = {fld.name: fld for fld in types[0].fields}
    assert fields_by_name["nested"].type == "Map<String, List<Integer>>"


def test_generic_return_type_rendered(tmp_path):
    """Methods returning generic types should have full type in return_type."""
    f = tmp_path / "GenericContainer.java"
    f.write_text(GENERICS_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    types = ex.extract_types()
    methods_by_name = {m.name: m for m in types[0].methods}
    assert methods_by_name["getNames"].return_type == "List<String>"
    assert methods_by_name["getScores"].return_type == "Map<String, Integer>"
    assert methods_by_name["findFirst"].return_type == "Optional<String>"


def test_generic_param_type_rendered(tmp_path):
    """Method parameters with generic types should render fully."""
    f = tmp_path / "GenericContainer.java"
    f.write_text(GENERICS_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    types = ex.extract_types()
    process = next(m for m in types[0].methods if m.name == "process")
    assert process.parameters[0].type == "List<Integer>"


# -- Void return type ---------------------------------------------------------

VOID_JAVA = textwrap.dedent("""\
    package com.example;

    public class Actions {
        public void doSomething() {
        }

        public int compute() {
            return 42;
        }

        public Actions() {
        }
    }
""")


def test_void_method_return_type_is_void_string(tmp_path):
    """void methods should have return_type='void', not None."""
    f = tmp_path / "Actions.java"
    f.write_text(VOID_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    types = ex.extract_types()
    methods_by_name = {m.name: m for m in types[0].methods}
    assert methods_by_name["doSomething"].return_type == "void"


def test_non_void_method_return_type_preserved(tmp_path):
    """Non-void methods should still return their actual type."""
    f = tmp_path / "Actions.java"
    f.write_text(VOID_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    types = ex.extract_types()
    methods_by_name = {m.name: m for m in types[0].methods}
    assert methods_by_name["compute"].return_type == "int"


def test_constructor_return_type_is_none(tmp_path):
    """Constructors should still have return_type=None (no return type)."""
    f = tmp_path / "Actions.java"
    f.write_text(VOID_JAVA, encoding="utf-8")
    pr = JavaParser().parse(f)
    ex = JavaExtractor(pr.tree, pr.source, f, "com.example")
    types = ex.extract_types()
    ctors = [m for m in types[0].methods if m.is_constructor]
    assert len(ctors) == 1
    assert ctors[0].return_type is None
