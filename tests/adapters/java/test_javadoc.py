from inspect4all.adapters.java.javadoc_parser import parse_javadoc

JAVADOC = """\
/**
 * Adds two numbers.
 *
 * @param a first number
 * @param b second number
 * @return sum of a and b
 * @throws IllegalArgumentException if a or b is negative
 */
"""


def test_parse_javadoc_description():
    doc = parse_javadoc(JAVADOC)
    assert doc is not None
    assert "Adds two numbers" in doc.short_description


def test_parse_javadoc_params():
    doc = parse_javadoc(JAVADOC)
    assert "a" in doc.params
    assert "b" in doc.params


def test_parse_javadoc_return():
    doc = parse_javadoc(JAVADOC)
    assert doc.returns is not None
    assert "sum" in doc.returns.description


def test_parse_empty():
    doc = parse_javadoc(None)
    assert doc is None
