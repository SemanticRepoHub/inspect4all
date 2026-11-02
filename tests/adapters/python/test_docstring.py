from inspect4all.adapters.python.docstring_parser import extract_documentation


def test_google_style_docstring():
    ds = """Process raw data.

    Args:
        data: List of raw entries
        strict: If True, raise on errors

    Returns:
        Processed results dict

    Raises:
        ValueError: If data is empty
    """
    doc = extract_documentation(ds)
    assert doc.short_description == "Process raw data."
    assert "data" in doc.params
    assert doc.returns is not None
    assert doc.returns.description == "Processed results dict"
    assert len(doc.raises) == 1
    assert doc.raises[0].type == "ValueError"


def test_empty_docstring():
    doc = extract_documentation("")
    assert doc.short_description is None
    assert doc.params == {}


def test_simple_one_liner():
    doc = extract_documentation("Load the dataset.")
    assert doc.short_description == "Load the dataset."
    assert doc.long_description is None


def test_none_docstring():
    doc = extract_documentation(None)
    assert doc is None
