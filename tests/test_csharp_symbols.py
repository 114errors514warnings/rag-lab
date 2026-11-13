"""C# 符号索引：定义/方法/调用边（正则近似，够 ``get_symbol`` 用）。"""

from __future__ import annotations

from rag_engine.code_rag import build_dependency_graph, extract_csharp_symbols, index_code

SAMPLE = """\
using System;

namespace Game.Auth
{
    // 注释里的 FakeCall( 不应该被当成调用
    public class TokenService
    {
        private readonly IClock _clock;

        public TokenService(IClock clock)
        {
            _clock = clock;
        }

        public string IssueToken(string user)
        {
            Validate(user);
            return Sign(user, 15);
        }

        private void Validate(string user)
        {
            if (string.IsNullOrEmpty(user)) throw new ArgumentException("bad");
        }

        private string Sign(string user, int minutes) => $"{user}:{minutes}";
    }

    public class TokenController
    {
        public void Handle()
        {
            var service = new TokenService(null);
            service.IssueToken("alice");
        }
    }
}
"""


def _write(tmp_path, name="TokenService.cs"):
    path = tmp_path / name
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_extracts_classes_and_methods(tmp_path):
    chunks = extract_csharp_symbols(_write(tmp_path), tmp_path)
    symbols = {c.meta["symbol"]: c.meta["kind"] for c in chunks}
    assert symbols["TokenService"] == "class"
    assert symbols["TokenController"] == "class"
    assert symbols["TokenService.IssueToken"] == "method"
    assert symbols["TokenService.Validate"] == "method"
    assert symbols["TokenController.Handle"] == "method"


def test_dependencies_skip_keywords_and_comments(tmp_path):
    chunks = {c.meta["symbol"]: c for c in extract_csharp_symbols(_write(tmp_path), tmp_path)}
    deps = chunks["TokenService.IssueToken"].meta["deps"]
    assert "TokenService.Validate" in deps and "TokenService.Sign" in deps
    assert "FakeCall" not in deps          # 只在注释里
    assert not any(dep.split(".")[-1].lower() in {"if", "return", "new", "string"} for dep in deps)


def test_graph_links_callers(tmp_path):
    _write(tmp_path)
    graph = build_dependency_graph(index_code(tmp_path, extensions=[".cs"]))
    assert graph["TokenService.Validate"]["callers"] == ["TokenService.IssueToken"]
    assert graph["TokenService.IssueToken"]["callees"] == [
        "TokenService.Sign", "TokenService.Validate"]
    # 跨类调用只能按"方法名"连边（没有类型解析），所以这里验的是 Handle 认出了这两个名字
    handle = graph["TokenController.Handle"]["callees"]
    assert "TokenService" in handle and "IssueToken" in handle


def test_project_id_override_is_used(tmp_path):
    chunks = extract_csharp_symbols(_write(tmp_path), tmp_path, project_id="card-sim")
    assert {c.meta["project_id"] for c in chunks} == {"card-sim"}
    assert chunks[0].chunk_id.startswith("card-sim:")


def test_python_indexing_is_unchanged_by_default(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.cs").write_text("public class B { }", encoding="utf-8")
    default = index_code(tmp_path)
    assert [c.meta["symbol"] for c in default] == ["f"]      # 默认仍是只用 .py
    both = index_code(tmp_path, extensions=[".py", ".cs"])
    assert {"f", "B"} <= {c.meta["symbol"] for c in both}
