from __future__ import annotations

import re

from inspect4all.core.models import (
    Documentation,
    ExceptionDoc,
    ParamDoc,
    ReturnDoc,
)


def parse_javadoc(raw: str | None) -> Documentation | None:
    if not raw:
        return None

    text = raw.replace("/**", "").replace("*/", "")
    lines = [re.sub(r"^\s*\*\s?", "", ln).rstrip() for ln in text.splitlines()]
    cleaned = "\n".join(lines).strip()
    if not cleaned:
        return None

    parts = re.split(r"\n(?=@\w+)", cleaned)
    description = parts[0].strip()
    short = (
        description.splitlines()[0].rstrip(".").strip() if description else ""
    )

    params: dict[str, ParamDoc] = {}
    returns: ReturnDoc | None = None
    raises: list[ExceptionDoc] = []
    tags: dict[str, str] = {}

    for tag_block in parts[1:]:
        tag_block = tag_block.strip()
        if not tag_block.startswith("@"):
            continue
        tokens = tag_block.split(None, 2)
        tag_name = tokens[0][1:]  # strip @
        if tag_name == "param" and len(tokens) >= 2:
            pname = tokens[1]
            pdesc = tokens[2].strip() if len(tokens) > 2 else ""
            params[pname] = ParamDoc(description=pdesc, type=None)
        elif tag_name in ("return", "returns") and len(tokens) >= 2:
            rdesc = " ".join(tokens[1:]).strip()
            returns = ReturnDoc(description=rdesc, type=None)
        elif tag_name in ("throws", "exception") and len(tokens) >= 2:
            etype = tokens[1]
            edesc = tokens[2].strip() if len(tokens) > 2 else ""
            raises.append(ExceptionDoc(type=etype, description=edesc))
        else:
            tags[tag_name] = " ".join(tokens[1:]).strip()

    return Documentation(
        short_description=short,
        long_description=description if description != short else None,
        full_text=cleaned,
        params=params,
        returns=returns,
        raises=raises,
        tags=tags,
        enrichments=[],
    )
