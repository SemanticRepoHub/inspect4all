"""Main entry point for inspect4all."""

import logging
import time
from pathlib import Path

import click

from inspect4all import __version__
from inspect4all.core.constants import EmbeddingMode


def _enable_enrichment_logging() -> None:
    """Route enrichment INFO logs to stdout so progress is visible by default."""
    pkg = logging.getLogger("inspect4all.enrichment")
    if not pkg.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("  %(message)s"))
        pkg.addHandler(handler)
    pkg.setLevel(logging.INFO)
    pkg.propagate = False


class _DefaultToRunGroup(click.Group):
    """Route bare option-style invocations (e.g. `-i <repo>`) to `run`."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if (
            args
            and args[0] not in self.commands
            and args[0]
            not in (
                "--help",
                "-h",
                "--version",
            )
        ):
            args = ["run", *args]
        return super().parse_args(ctx, args)


@click.group(cls=_DefaultToRunGroup, invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """inspect4all - language-agnostic repository inspection and enrichment.

    Invoked without a subcommand but with options (e.g. `-i <repo>`),
    it runs the full pipeline: inspect, then LLM enrichment.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


_INSPECT_OPTIONS = [
    click.option(
        "-i",
        "--input_path",
        required=True,
        type=click.Path(exists=True, path_type=Path),
        help="Input path of the file or directory to inspect.",
    ),
    click.option(
        "-o",
        "--output_dir",
        type=click.Path(path_type=Path),
        help="Output directory path to store results. "
        "If the directory does not exist, the tool will create it.",
    ),
    click.option(
        "-ignore_dir",
        "--ignore_dir_pattern",
        multiple=True,
        help="Ignore directories starting with a certain pattern. "
        "This parameter can be provided multiple times to ignore multiple directory patterns.",
    ),
    click.option(
        "-ignore_file",
        "--ignore_file_pattern",
        multiple=True,
        help="Ignore files starting with a certain pattern. "
        "This parameter can be provided multiple times to ignore multiple file patterns.",
    ),
    click.option(
        "-r",
        "--requirements",
        is_flag=True,
        help="Find the library dependencies of the repository.",
    ),
    click.option(
        "-html",
        "--html_output",
        is_flag=True,
        help="Generates an HTML file of the DirJson in the output directory.",
    ),
    click.option(
        "-si",
        "--software_invocation",
        is_flag=True,
        help="Generates software invocation commands to run and test the target repository.",
    ),
    click.option(
        "-ee",
        "--embedding_export",
        is_flag=True,
        help="Write embedding_export.json with the four-level "
        "embedding-ready text records (README, CODE, DOCUMENTATION, TOTAL).",
    ),
    click.option(
        "-ld",
        "--license_detection",
        is_flag=True,
        help="Detects the license of the target repository.",
    ),
    click.option(
        "-rm",
        "--readme",
        is_flag=True,
        help="Extract all README files in the target repository.",
    ),
    click.option(
        "-md",
        "--metadata",
        is_flag=True,
        help="Extract metadata of the target repository using GitHub API.",
    ),
    click.option(
        "--verbose", "-v", is_flag=True, help="Enable verbose output."
    ),
    click.option(
        "--all",
        "all_features",
        is_flag=True,
        help="Enable all analysis features.",
    ),
]


def _inspect_options(f):
    for option in reversed(_INSPECT_OPTIONS):
        f = option(f)
    return f


def _enrich_or_warn(result, output_dir: Path) -> None:
    """Run enrichment on an in-memory analysis; warn instead of failing.

    The inspection outputs are already on disk at this point; an
    unreachable LLM server must not turn a successful inspection into a
    failed run.
    """
    from inspect4all.enrichment.llm import LLMSettings, build_chat_model
    from inspect4all.enrichment.runner import (
        enrich_repo,
        write_enriched_outputs,
    )

    _enable_enrichment_logging()
    try:
        settings = LLMSettings()
        model = build_chat_model(settings)
        _t0 = time.perf_counter()
        enrichment = enrich_repo(
            result,
            model=model,
            model_id=settings.model,
            cache_path=output_dir / "enrichment_cache.jsonl",
        )
        _enrich_elapsed = time.perf_counter() - _t0
        write_enriched_outputs(output_dir, result, EmbeddingMode.ENRICHED)
        s = enrichment.stats
        click.secho(
            f"Enrichment: {s['enriched']} enriched, {s['failed']} failed, "
            f"{s['skipped']} skipped.  ({_enrich_elapsed:.3f}s)",
            fg="green",
        )
    except Exception as e:
        click.secho(
            f"Warning: enrichment failed ({type(e).__name__}: {e}); "
            "inspection outputs are unaffected.",
            fg="yellow",
            err=True,
        )


def _run_inspection(
    input_path: Path,
    output_dir: Path | None,
    ignore_dir_pattern: tuple[str, ...],
    ignore_file_pattern: tuple[str, ...],
    requirements: bool,
    html_output: bool,
    software_invocation: bool,
    embedding_export: bool,
    license_detection: bool,
    readme: bool,
    metadata: bool,
    verbose: bool,
    all_features: bool,
    enrich_flag: bool,
):
    from inspect4all.adapters import build_default_registry
    from inspect4all.output.embedding_export import EmbeddingExporter
    from inspect4all.output.json_writer import JsonWriter
    from inspect4all.pipeline import InspectionPipeline, InspectOptions

    if output_dir is None:
        output_dir = Path.cwd() / "inspect4all_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        click.echo(f"Input path: {input_path}")
        click.echo(f"Output directory: {output_dir}")

    try:
        options = InspectOptions(
            ignore_dir_patterns=list(ignore_dir_pattern),
            ignore_file_patterns=list(ignore_file_pattern),
            extract_dependencies=requirements or all_features,
            detect_software_type=software_invocation or all_features,
            extract_license=license_detection or all_features,
            extract_readme=readme or all_features,
            extract_metadata=metadata or all_features,
            all_features=all_features,
        )

        with click.progressbar(length=5, label="Inspecting repository") as bar:
            pipeline = InspectionPipeline(build_default_registry())
            bar.update(1)
            _t_inspect = time.perf_counter()
            result = pipeline.inspect(input_path, options)
            _inspect_elapsed = time.perf_counter() - _t_inspect
            bar.update(3)
            writer = JsonWriter(output_dir=output_dir)
            json_path = writer.write(result)
            if html_output or all_features:
                import json as _json

                from json2html import json2html as _j2h

                data = _json.loads(json_path.read_text())
                html = _j2h.convert(json=data)
                (output_dir / "repository_analysis.html").write_text(html)
            if all_features or embedding_export:
                import json as _json

                exporter = EmbeddingExporter()
                export = exporter.export(result, EmbeddingMode.ORIGINAL)
                (output_dir / "embedding_export.json").write_text(
                    _json.dumps(export, indent=2, default=str)
                )
            if enrich_flag:
                _enrich_or_warn(result, output_dir)
            bar.update(1)

        click.echo()
        click.secho("✓ Inspection complete!", fg="green", bold=True)
        click.secho(f"  Inspection time: {_inspect_elapsed:.3f}s", fg="cyan")
        click.echo(f"\nResults saved to: {output_dir}")

        if verbose:
            click.echo("\nGenerated files:")
            for file in sorted(output_dir.glob("*")):
                click.echo(f"  - {file.name}")

    except FileNotFoundError as e:
        raise click.ClickException(f"Input path not found: {e.filename}") from e

    except PermissionError as e:
        raise click.ClickException(f"Permission denied: {e.filename}") from e

    except KeyboardInterrupt:
        click.echo("\n\nInspection cancelled by user.", err=True)
        raise click.Abort() from None

    except Exception as e:
        if verbose:
            click.secho("\n✗ Unexpected error occurred:", fg="red", err=True)
            import traceback

            click.echo(traceback.format_exc(), err=True)
            raise click.Abort() from e
        else:
            raise click.ClickException(
                f"{type(e).__name__}: {e}\nRun with --verbose for more details."
            ) from e


@main.command(name="inspect")
@_inspect_options
@click.option(
    "--enrich",
    "enrich_flag",
    is_flag=True,
    help="After inspecting, run LLM docstring enrichment on undocumented "
    "records and write repository_analysis.enriched.json alongside.",
)
def inspect(**kwargs):
    """Inspect a repository and write the structural analysis.

    Analyzes repositories to extract structure, dependencies,
    documentation, and metadata.
    """
    _run_inspection(**kwargs)


@main.command(name="run")
@_inspect_options
def run(**kwargs):
    """Inspect a repository, then enrich it (the no-subcommand default)."""
    _run_inspection(enrich_flag=True, **kwargs)


@main.command(name="enrich")
@click.option(
    "-i",
    "--input_dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Output directory containing a prior repository_analysis.json.",
)
@click.option("--model", default=None, help="Override INSPECT4ALL_LLM_MODEL.")
@click.option(
    "--base-url", default=None, help="Override INSPECT4ALL_LLM_BASE_URL."
)
@click.option(
    "--api-key", default=None, help="Override INSPECT4ALL_LLM_API_KEY."
)
@click.option(
    "--temperature",
    type=float,
    default=None,
    help="Override INSPECT4ALL_LLM_TEMPERATURE.",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Override INSPECT4ALL_LLM_MAX_TOKENS.",
)
@click.option(
    "--reasoning-effort",
    default=None,
    help='Override INSPECT4ALL_LLM_REASONING_EFFORT (e.g. "none" to disable thinking).',
)
@click.option(
    "--max-records",
    type=int,
    default=None,
    help="Cap the number of records to enrich (cost control).",
)
@click.option(
    "--mode",
    type=click.Choice(["enriched", "combined"]),
    default="enriched",
    help="Embedding export mode for the enriched output.",
)
@click.option(
    "--processors",
    type=click.Choice(["docstrings", "java-backfill"]),
    multiple=True,
    help="Enrichers to run. Repeat to combine: --processors docstrings "
    "--processors java-backfill. Defaults to all when omitted.",
)
@click.option(
    "--docstring-target",
    type=click.Choice(["undocumented", "all"]),
    default="undocumented",
    help="Which functions the docstring enricher considers. "
    '"undocumented" (default) skips already-documented functions; '
    '"all" re-enriches everything including documented functions.',
)
def enrich(
    input_dir: Path,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    temperature: float | None,
    max_tokens: int | None,
    reasoning_effort: str | None,
    max_records: int | None,
    mode: str,
    processors: tuple[str, ...],
    docstring_target: str,
) -> None:
    """Enrich a prior analysis with LLM-generated docstrings."""
    from inspect4all.enrichment.llm import LLMSettings, build_chat_model
    from inspect4all.enrichment.runner import _ALL_PROCESSORS, run_enrichment

    _enable_enrichment_logging()
    settings = LLMSettings()
    chat_model = build_chat_model(
        settings,
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    )
    model_id = model or settings.model
    _t0 = time.perf_counter()
    enrichment = run_enrichment(
        input_dir,
        model=chat_model,
        model_id=model_id,
        max_records=max_records,
        mode=EmbeddingMode(mode),
        processors=processors or _ALL_PROCESSORS,
        docstring_target=docstring_target,
    )
    _elapsed = time.perf_counter() - _t0
    s = enrichment.stats
    _done = s["enriched"] + s["failed"]
    _avg = f"  avg {_elapsed / _done:.3f}s/file" if _done else ""
    click.secho(
        f"Enriched {s['enriched']}, failed {s['failed']}, "
        f"skipped {s['skipped']}.  Total: {_elapsed:.3f}s{_avg}",
        fg="green",
    )
    if s["enriched"] == 0 and s["failed"] > 0:
        raise click.ClickException(
            "No records enriched despite targets present; "
            "check --base-url / model configuration."
        )


if __name__ == "__main__":
    main()
