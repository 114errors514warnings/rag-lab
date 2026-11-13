"""C# 符号扫描（阶段五扩展）：class / struct / interface / enum / record + 方法。

**为什么是正则而不是解析器**：C# 没有标准库 AST，引 Roslyn 会拖一个几百 MB 的依赖；
这里只需要"定义在哪、谁调谁"，一条**按花括号深度走行**的规则够用。
已知取舍（不修）：属性、事件、局部函数、表达式体成员的边界可能不准；
跨文件只按**同名符号**连边（与 Python 侧一致）。

产出的 ``Chunk`` 形状与 ``ast_indexer`` 完全一致，因此
``build_dependency_graph`` / ``get_symbol`` 不需要分语言。
"""

from __future__ import annotations

import re
from pathlib import Path

from ..schema import Chunk

#: 出现在调用位置但不是"被调用符号"的词
_KEYWORDS = {
    "if", "for", "foreach", "while", "switch", "catch", "using", "lock", "fixed",
    "return", "new", "throw", "typeof", "sizeof", "nameof", "default", "checked",
    "unchecked", "base", "this", "get", "set", "add", "remove", "value", "when",
    "await", "yield", "in", "is", "as", "out", "ref", "params", "do", "else",
    "try", "finally", "case", "goto", "delegate", "where", "select", "from",
    "let", "orderby", "group", "join", "on", "equals", "into", "by",
}

_MODIFIERS = (
    "public|private|protected|internal|static|virtual|override|abstract|sealed|"
    "partial|async|unsafe|extern|new|readonly|required|volatile|const"
)

_CLASS_RE = re.compile(r"\b(class|struct|interface|enum|record)\s+([A-Za-z_]\w*)")
_METHOD_RE = re.compile(
    rf"^\s*(?:\[[^\]]*\]\s*)*"
    rf"(?:(?:{_MODIFIERS})\s+)*"
    r"(?:[\w<>\[\],\.\?]+\s+)+"
    r"([A-Za-z_]\w*)\s*\("
)
_CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


def _blank_out(source: str) -> list[str]:
    """把注释与字符串内容替换成空格（保留换行与列宽），避免把注释里的词当符号。"""
    out: list[str] = []
    i, n = 0, len(source)
    mode = None          # None | "line" | "block" | "string" | "verbatim" | "char"
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if mode is None:
            if ch == "/" and nxt == "/":
                mode = "line"
                out.append("  ")
                i += 2
                continue
            if ch == "/" and nxt == "*":
                mode = "block"
                out.append("  ")
                i += 2
                continue
            if ch == "@" and nxt == '"':
                mode = "verbatim"
                out.append('@"')
                i += 2
                continue
            if ch == '"':
                mode = "string"
                out.append('"')
                i += 1
                continue
            if ch == "'":
                mode = "char"
                out.append("'")
                i += 1
                continue
            out.append(ch)
            i += 1
            continue
        if mode == "line":
            if ch == "\n":
                mode = None
                out.append("\n")
            else:
                out.append(" ")
            i += 1
            continue
        if mode == "block":
            if ch == "*" and nxt == "/":
                mode = None
                out.append("  ")
                i += 2
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
            continue
        if mode == "verbatim":
            if ch == '"' and nxt == '"':
                out.append("  ")
                i += 2
                continue
            if ch == '"':
                mode = None
                out.append('"')
                i += 1
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
            continue
        # string / char：处理转义
        if ch == "\\" and i + 1 < n:
            out.append("  " if source[i + 1] != "\n" else " \n")
            i += 2
            continue
        if (mode == "string" and ch == '"') or (mode == "char" and ch == "'"):
            mode = None
            out.append(ch)
            i += 1
            continue
        out.append("\n" if ch == "\n" else " ")
        i += 1
    return "".join(out).splitlines()


def _match_brace(lines: list[str], start: int, column: int = 0) -> int:
    depth = 0
    for index in range(start, len(lines)):
        segment = lines[index][column:] if index == start else lines[index]
        for ch in segment:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return index
    return len(lines) - 1


def _deps(text: str) -> list[str]:
    return sorted({name for name in _CALL_RE.findall(text) if name.lower() not in _KEYWORDS})


def extract_csharp_symbols(path: Path | str, root: Path | str,
                           project_id: str | None = None) -> list[Chunk]:
    path, root = Path(path), Path(root)
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    default_project = rel.split("/", 1)[0] if "/" in rel else "root"
    project = project_id or default_project
    rel_in_project = rel.split("/", 1)[1] if (project_id is None and "/" in rel) else rel
    source = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = _blank_out(source)

    chunks: list[Chunk] = []
    classes: list[tuple[str, int, int]] = []      # (类名, 起始行, 结束行)

    def add(name: str, kind: str, start: int, end: int, body: str,
            deps_source: str | None = None) -> None:
        """``deps_source`` 用来只从"方法体 + 签名右侧"里提调用，避免把声明行自身算成依赖。"""
        chunks.append(Chunk(
            chunk_id=f"{project}:{rel_in_project}:{name}",
            doc_id=f"{project}:{rel_in_project}",
            text=body,
            meta={
                "symbol": name, "kind": kind, "file": rel_in_project,
                "project_id": project, "source": rel,
                "start_line": start + 1, "end_line": end + 1,
                # 类的 deps 不取"体内所有调用"：那会把每个方法都算成类的 callee，
                # 反过来污染 callers（方法会多出一个"类"调用方）。类只留空。
                "deps": [] if kind != "method" else _deps(deps_source if deps_source is not None else body),
            },
        ))

    # 第一遍：类（含 struct/interface/enum/record）及其花括号范围
    for index, line in enumerate(lines):
        class_match = _CLASS_RE.search(line)
        if not class_match:
            continue
        name = class_match.group(2)
        end = _match_brace(lines, index, class_match.end())
        add(name, class_match.group(1), index, end, "\n".join(lines[index:end + 1]))
        classes.append((name, index, end))

    # 第二遍：方法 —— 归属到"包含它的最内层类"（兼容 Allman 风格：`{` 在下一行）
    for index, line in enumerate(lines):
        if _CLASS_RE.search(line) or "(" not in line:
            continue
        method_match = _METHOD_RE.match(line)
        if not method_match or method_match.group(1).lower() in _KEYWORDS:
            continue
        rest = line[method_match.end():]
        looks_like_body = bool(re.search(r"\)\s*(?:\{|=>)", rest)) or "=>" in rest
        if not looks_like_body:
            nxt = next((item.strip() for item in lines[index + 1:] if item.strip()), "")
            looks_like_body = nxt.startswith("{")
        if not looks_like_body:
            continue
        owners = [item for item in classes if item[1] < index <= item[2]]
        if not owners:
            continue
        owner = max(owners, key=lambda item: item[1])[0]
        end = _match_brace(lines, index, method_match.end() - 1)
        add(f"{owner}.{method_match.group(1)}", "method", index, end,
            "\n".join(lines[index:end + 1]),
            deps_source=line[method_match.end():] + "\n" + "\n".join(lines[index + 1:end + 1]))

    # 第三遍：把调用名尽量限定到"本类的方法名"，这样 deps 能和 graph 的 key 对上
    # （跨类调用没有类型解析，只能保持裸名——这是已知取舍）。
    symbols = {item.meta["symbol"] for item in chunks}
    for item in chunks:
        owner = item.meta["symbol"].split(".", 1)[0]
        resolved: list[str] = []
        for dep in item.meta.get("deps", []):
            for candidate in (f"{owner}.{dep}", dep):
                if candidate in symbols:
                    resolved.append(candidate)
                    break
            else:
                resolved.append(dep)
        item.meta["deps"] = sorted(set(resolved))

    return chunks
