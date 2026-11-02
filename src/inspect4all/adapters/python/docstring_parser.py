from __future__ import annotations

from docstring_parser import parse as dp_parse

from inspect4all.core.models import (
    Documentation,
    ExceptionDoc,
    ParamDoc,
    ReturnDoc,
)


def extract_documentation(docstring: str | None) -> Documentation | None:
    if docstring is None:
        return None
    if not docstring.strip():
        return Documentation(
            short_description=None,
            long_description=None,
            full_text=None,
            params={},
            returns=None,
            raises=[],
            tags={},
        )
    parsed = dp_parse(docstring)
    params = {
        p.arg_name: ParamDoc(description=p.description, type=p.type_name)
        for p in parsed.params
    }
    returns = None
    if parsed.returns:
        returns = ReturnDoc(
            description=parsed.returns.description,
            type=parsed.returns.type_name,
        )
    raises = [
        ExceptionDoc(type=r.type_name or "Exception", description=r.description)
        for r in parsed.raises
    ]
    tags: dict[str, str] = {}
    for meta in parsed.meta:
        if hasattr(meta, "args") and meta.args and meta.description:
            key = " ".join(meta.args)
            tags[key] = meta.description
    return Documentation(
        short_description=parsed.short_description or None,
        long_description=parsed.long_description or None,
        full_text=docstring,
        params=params,
        returns=returns,
        raises=raises,
        tags=tags,
    )
