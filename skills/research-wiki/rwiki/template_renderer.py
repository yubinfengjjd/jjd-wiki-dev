"""Parameter question schema and sandboxed Jinja2 template renderer.

Derived from ``copier-org/copier``:
- ``copier/_template.py``: ``filter_config`` (separating ``_``-prefixed template
  metadata from question definitions) and YAML config loading.
- ``copier/_user_data.py``: ``Question`` schema (``var_name``, ``type``, ``default``,
  ``choices``, ``multiselect``, ``help``, ``placeholder``, ``validator``, ``when``,
  ``ask``, ``secret``), type casting, and Jinja2 validation expressions.
- ``copier/_jinja_ext.py``: ``SandboxedEnvironment`` and path-confined
  ``CopierTemplateLoader`` preventing directory traversal outside ``template_root``.

Adapted for ``research-wiki`` Template Studio (both Tier 1 schema-driven
``wiki/templates/*/spec.json`` templates and Tier 2 L1 recipe/method scripts).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any

import yaml

try:
    from jinja2 import BaseLoader, Environment, FileSystemLoader, StrictUndefined, TemplateError
    from jinja2.sandbox import SandboxedEnvironment as _JinjaSandboxedEnvironment
    _HAS_JINJA2 = True
except ModuleNotFoundError:
    BaseLoader = object  # type: ignore[assignment,misc]
    Environment = Any  # type: ignore[assignment,misc]
    FileSystemLoader = object  # type: ignore[assignment,misc]
    StrictUndefined = object  # type: ignore[assignment,misc]

    class TemplateError(Exception):  # type: ignore[no-redef]
        pass

    class _JinjaSandboxedEnvironment:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("缺少 Jinja2 依赖，无法创建沙箱模板环境")

    _HAS_JINJA2 = False

try:
    from .esquisse_codegen import load_ggsci_palettes, resolve_palette
except ImportError:
    from esquisse_codegen import load_ggsci_palettes, resolve_palette

_UNSAFE_ATTRS = frozenset({"parse_file", "parse_raw", "from_file", "parser"})

CAST_STR_TO_NATIVE: dict[str, Callable[[Any], Any]] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": lambda v: v if isinstance(v, bool) else str(v).strip().lower() in {"1", "true", "yes", "y", "on"},
    "boolean": lambda v: v if isinstance(v, bool) else str(v).strip().lower() in {"1", "true", "yes", "y", "on"},
    "json": lambda v: json.loads(v) if isinstance(v, str) else v,
    "yaml": lambda v: yaml.safe_load(v) if isinstance(v, str) else v,
}


class ForbiddenTemplatePathError(PermissionError):
    """Raised when a template path escapes its declared template_root."""


class ParameterValidationError(ValueError):
    """Raised when user-supplied parameters fail Copier schema validation."""


# ---------------------------------------------------------------------------
# 1. Sandboxed Jinja2 environment & path-confined loader (copier/_jinja_ext.py)
# ---------------------------------------------------------------------------


class SandboxedTemplateEnvironment(_JinjaSandboxedEnvironment):
    """Sandboxed Jinja2 environment blocking unsafe model/path attributes."""

    def is_safe_attribute(self, obj: Any, attr: str, value: Any) -> bool:
        if attr in _UNSAFE_ATTRS:
            return False
        if isinstance(obj, PurePath) and attr == "parser":
            return False
        return super().is_safe_attribute(obj, attr, value)


class ConfinedTemplateLoader(FileSystemLoader):
    """Port of ``CopierTemplateLoader`` confining template resolution to ``template_root``."""

    def __init__(self, template_root: Path) -> None:
        self._root = template_root.resolve()
        super().__init__([str(self._root)])

    def get_source(self, environment: Environment, template: str) -> tuple[str, str, Callable[[], bool]]:
        source, filename, uptodate = super().get_source(environment, template)
        resolved = Path(filename).resolve()
        if not resolved.is_relative_to(self._root):
            raise ForbiddenTemplatePathError(f"Template path outside root: {resolved}")
        return source, filename, uptodate


def build_jinja_env(
    template_root: Path | None = None,
    *,
    strict: bool = False,
    palettes_db: dict[str, Any] | None = None,
) -> SandboxedTemplateEnvironment:
    """Create a sandboxed Jinja2 environment with R/Python/ggsci helper filters."""
    if not _HAS_JINJA2:
        raise RuntimeError("缺少 Jinja2 依赖，无法渲染包含 Jinja2 语法的模板")
    loader: BaseLoader | None = ConfinedTemplateLoader(template_root) if template_root else None
    env = SandboxedTemplateEnvironment(
        loader=loader,
        undefined=StrictUndefined if strict else _default_undefined(),
        keep_trailing_newline=True,
    )
    palettes = palettes_db if palettes_db is not None else load_ggsci_palettes()

    def _r_quote(val: Any) -> str:
        s = str(val).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'

    def _r_vec(vals: list[Any]) -> str:
        return "c(" + ", ".join(_r_quote(v) for v in vals) + ")"

    def _ggsci_colors(name: str) -> list[str]:
        return list(resolve_palette(str(name), palettes).get("colors", []))

    env.filters["r_quote"] = _r_quote
    env.filters["r_vec"] = _r_vec
    env.filters["py_repr"] = repr
    env.filters["to_json"] = lambda v: json.dumps(v, ensure_ascii=False)
    env.filters["ggsci_colors"] = _ggsci_colors
    return env


def _default_undefined():
    from jinja2 import Undefined

    return Undefined


# ---------------------------------------------------------------------------
# 2. Copier Question Schema & Spec Adapter (copier/_template.py & _user_data.py)
# ---------------------------------------------------------------------------


@dataclass
class ParameterQuestion:
    """Normalized parameter question schema derived from ``copier.yml`` Question."""

    var_name: str
    type: str = "str"
    default: Any = None
    choices: list[Any] | dict[str, Any] = field(default_factory=list)
    multiselect: bool = False
    help: str = ""
    placeholder: str = ""
    validator: str = ""
    when: str | bool = True
    ask: str | bool = True
    secret: bool = False
    label: str = ""
    min_value: float | None = None
    max_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.var_name,
            "var_name": self.var_name,
            "label": self.label or self.var_name,
            "type": self.type,
            "default": self.default,
            "choices": self.choices,
            "multiselect": self.multiselect,
            "help": self.help,
            "placeholder": self.placeholder,
            "validator": self.validator,
            "when": self.when,
            "secret": self.secret,
            "min": self.min_value,
            "max": self.max_value,
        }


def filter_config(data: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Port of ``copier._template.filter_config`` separating ``_`` config keys and questions."""
    config_data: dict[str, Any] = {}
    questions_data: dict[str, dict[str, Any]] = {}
    for k, v in data.items():
        if k.startswith("_"):
            config_data[k[1:]] = v
        else:
            questions_data[k] = dict(v) if isinstance(v, Mapping) else {"default": v}
    return config_data, questions_data


def load_copier_yaml(conf_path: Path) -> tuple[dict[str, Any], list[ParameterQuestion]]:
    """Load a ``copier.yml`` / ``copier.yaml`` file into ``(config, questions)``."""
    raw = yaml.safe_load(conf_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"Expected mapping in {conf_path}")
    cfg, qdict = filter_config(raw)
    return cfg, spec_parameters_to_questions(qdict)


def spec_parameters_to_questions(raw_params: Any) -> list[ParameterQuestion]:
    """Convert either ``spec.json['parameters']`` or ``copier.yml`` questions into ``ParameterQuestion`` objects."""
    questions: list[ParameterQuestion] = []
    if isinstance(raw_params, Mapping):
        items = [(k, v if isinstance(v, Mapping) else {"default": v}) for k, v in raw_params.items()]
    elif isinstance(raw_params, list):
        items = [
            (str(item.get("name") or item.get("var_name")), item)
            for item in raw_params
            if isinstance(item, Mapping) and (item.get("name") or item.get("var_name"))
        ]
    else:
        return questions

    for name, q in items:
        qtype = str(q.get("type") or "")
        default = q.get("default")
        if not qtype:
            if isinstance(default, bool):
                qtype = "bool"
            elif isinstance(default, int):
                qtype = "int"
            elif isinstance(default, float):
                qtype = "float"
            else:
                qtype = "str"
        questions.append(
            ParameterQuestion(
                var_name=name,
                type=qtype,
                default=default,
                choices=q.get("choices") or [],
                multiselect=bool(q.get("multiselect", False)),
                help=str(q.get("help") or q.get("description") or ""),
                placeholder=str(q.get("placeholder") or ""),
                validator=str(q.get("validator") or ""),
                when=q.get("when", True),
                ask=q.get("ask", True),
                secret=bool(q.get("secret", False)),
                label=str(q.get("label") or name),
                min_value=q.get("min"),
                max_value=q.get("max"),
            )
        )
    return questions


def _has_jinja_markers(text: str) -> bool:
    return any(token in text for token in ("{{", "{%", "{#"))


def validate_and_resolve_answers(
    questions: list[ParameterQuestion],
    provided: Mapping[str, Any] | None = None,
    env: SandboxedTemplateEnvironment | None = None,
) -> dict[str, Any]:
    """Validate & cast parameters against Copier-style ``ParameterQuestion`` rules."""
    provided = dict(provided or {})
    answers: dict[str, Any] = {}

    def _get_env() -> SandboxedTemplateEnvironment:
        nonlocal env
        if env is None:
            env = build_jinja_env()
        return env

    for q in questions:
        # Evaluate `when` condition if templated
        if isinstance(q.when, str):
            stripped = q.when.strip().lower()
            if not _has_jinja_markers(q.when) and stripped in {"true", "false", "1", "0", "yes", "no", ""}:
                if stripped in {"false", "0", "no", ""}:
                    continue
            else:
                try:
                    rendered_when = _get_env().from_string(q.when).render(**answers, **provided).strip().lower()
                    if rendered_when in {"false", "0", "no", ""}:
                        continue
                except TemplateError:
                    pass
        elif q.when is False:
            continue

        raw_val = provided.get(q.var_name, q.default)
        if raw_val is None:
            answers[q.var_name] = None
            continue

        caster = CAST_STR_TO_NATIVE.get(q.type.lower(), lambda v: v)
        try:
            val = caster(raw_val)
        except (TypeError, ValueError) as exc:
            raise ParameterValidationError(
                f"Parameter '{q.var_name}' expected {q.type}, got {raw_val!r}"
            ) from exc

        # Choices check
        if q.choices:
            valid_choices = list(q.choices.values()) if isinstance(q.choices, Mapping) else list(q.choices)
            if q.multiselect and isinstance(val, list):
                invalid = [x for x in val if x not in valid_choices]
                if invalid:
                    raise ParameterValidationError(f"Invalid choices for '{q.var_name}': {invalid}")
            elif val not in valid_choices:
                raise ParameterValidationError(
                    f"Parameter '{q.var_name}'={val!r} must be one of {valid_choices}"
                )

        # Numeric bounds check
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if q.min_value is not None and val < q.min_value:
                raise ParameterValidationError(f"Parameter '{q.var_name}'={val} < min {q.min_value}")
            if q.max_value is not None and val > q.max_value:
                raise ParameterValidationError(f"Parameter '{q.var_name}'={val} > max {q.max_value}")

        # Copier Jinja2 validator check (empty rendered output = valid)
        if q.validator:
            try:
                err_msg = _get_env().from_string(q.validator).render(**answers, **{q.var_name: val}).strip()
                if err_msg:
                    raise ParameterValidationError(f"Parameter '{q.var_name}': {err_msg}")
            except TemplateError as exc:
                raise ParameterValidationError(f"Validator error for '{q.var_name}': {exc}") from exc

        answers[q.var_name] = val

    # Preserve extra non-schema keys supplied by caller (e.g. Studio custom overrides)
    for k, v in provided.items():
        if k not in answers:
            answers[k] = v
    return answers


# ---------------------------------------------------------------------------
# 3. Unified Studio Code Renderer (Jinja2 + Parameter/Bindings Header Injection)
# ---------------------------------------------------------------------------


def build_parameter_header(
    language: str,
    *,
    data_file: str = "",
    bindings: Mapping[str, str] | None = None,
    parameters: Mapping[str, Any] | None = None,
    palette_colors: list[str] | None = None,
) -> str:
    """Emit a safe, executable Python/R preamble injecting Studio parameters & bindings."""
    bindings_dict = dict(bindings or {})
    params_dict = dict(parameters or {})
    colors = palette_colors or []

    if language.lower() == "r":
        lines = [
            "# --- Research-Wiki Studio Parameters (Copier/ggsci) ---",
            f'RWIKI_DATA_FILE <- {json.dumps(data_file)}',
            f'RWIKI_BINDINGS_JSON <- {json.dumps(json.dumps(bindings_dict, ensure_ascii=False))}',
            f'RWIKI_PARAMS_JSON <- {json.dumps(json.dumps(params_dict, ensure_ascii=False))}',
            f'Sys.setenv(RWIKI_DATA_FILE = RWIKI_DATA_FILE, RWIKI_BINDINGS_JSON = RWIKI_BINDINGS_JSON, RWIKI_PARAMS_JSON = RWIKI_PARAMS_JSON)',
        ]
        if colors:
            vec = ", ".join(json.dumps(c) for c in colors)
            lines.append(f"RWIKI_PALETTE_COLORS <- c({vec})")
        for k, v in params_dict.items():
            if k.isidentifier():
                if isinstance(v, bool):
                    lines.append(f"PARAM_{k.upper()} <- {'TRUE' if v else 'FALSE'}")
                elif isinstance(v, (int, float)):
                    lines.append(f"PARAM_{k.upper()} <- {v}")
                elif isinstance(v, str):
                    lines.append(f"PARAM_{k.upper()} <- {json.dumps(v)}")
        lines.append("# --- End Studio Parameters ---")
        return "\n".join(lines) + "\n\n"

    lines = [
        "# --- Research-Wiki Studio Parameters (Copier/ggsci) ---",
        "import json as _rwiki_json, os as _rwiki_os",
        f"RWIKI_DATA_FILE = {data_file!r}",
        f"RWIKI_BINDINGS = {bindings_dict!r}",
        f"RWIKI_PARAMS = {params_dict!r}",
        f"RWIKI_PALETTE_COLORS = {colors!r}",
        "_rwiki_os.environ['RWIKI_DATA_FILE'] = RWIKI_DATA_FILE",
        "_rwiki_os.environ['RWIKI_BINDINGS_JSON'] = _rwiki_json.dumps(RWIKI_BINDINGS, ensure_ascii=False)",
        "_rwiki_os.environ['RWIKI_PARAMS_JSON'] = _rwiki_json.dumps(RWIKI_PARAMS, ensure_ascii=False)",
    ]
    for k, v in params_dict.items():
        if k.isidentifier():
            lines.append(f"PARAM_{k.upper()} = {v!r}")
    lines.append("# --- End Studio Parameters ---")
    return "\n".join(lines) + "\n\n"


def render_template_code(
    template_source: str,
    *,
    language: str = "python",
    spec: Mapping[str, Any] | None = None,
    parameters: Mapping[str, Any] | None = None,
    bindings: Mapping[str, str] | None = None,
    data_file: str = "",
    project_dir: str = "",
    template_root: Path | None = None,
    inject_header: bool = True,
) -> dict[str, Any]:
    """Render a template (Jinja2 or parameter-injected Python/R) using Copier patterns.

    Returns ``{ code, language, parameters, bindings_json, palette }``.
    """
    spec = dict(spec or {})
    questions = spec_parameters_to_questions(spec.get("parameters"))
    has_jinja_syntax = _has_jinja_markers(template_source)
    env = build_jinja_env(template_root=template_root) if has_jinja_syntax else None
    resolved_params = validate_and_resolve_answers(questions, parameters, env=env)

    palette_name = str(resolved_params.get("palette") or "NPG")
    palette_entry = resolve_palette(palette_name)
    palette_colors = list(palette_entry.get("colors", []))

    if has_jinja_syntax:
        assert env is not None
        ctx = {
            **resolved_params,
            "parameters": resolved_params,
            "bindings": dict(bindings or {}),
            "data_file": data_file,
            "project_dir": project_dir,
            "palette_name": palette_entry.get("id", palette_name),
            "palette_colors": palette_colors,
            "r_scale_color": palette_entry.get("r_scale_color", "ggsci::scale_color_npg()"),
            "r_scale_fill": palette_entry.get("r_scale_fill", "ggsci::scale_fill_npg()"),
        }
        rendered_body = env.from_string(template_source).render(**ctx)
    else:
        rendered_body = template_source

    if inject_header and not has_jinja_syntax:
        header = build_parameter_header(
            language,
            data_file=data_file,
            bindings=bindings,
            parameters=resolved_params,
            palette_colors=palette_colors,
        )
        code = header + rendered_body
    else:
        code = rendered_body

    return {
        "code": code,
        "language": language,
        "parameters": resolved_params,
        "bindings_json": json.dumps(dict(bindings or {}), ensure_ascii=False, indent=2),
        "palette": palette_entry,
    }
