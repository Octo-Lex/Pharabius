"""Tests for Rust import extraction in scanner."""

from pharabius.core.scanner import _extract_rust_imports


class TestRustSimpleUse:
    def test_crate_simple(self):
        text = "use crate::foo::bar;\n"
        assert _extract_rust_imports(text) == ["crate::foo::bar"]

    def test_crate_deep(self):
        text = "use crate::engine::network::handler;\n"
        assert _extract_rust_imports(text) == ["crate::engine::network::handler"]

    def test_super_import(self):
        text = "use super::module;\n"
        assert _extract_rust_imports(text) == ["super::module"]

    def test_self_import(self):
        text = "use self::item;\n"
        assert _extract_rust_imports(text) == ["self::item"]

    def test_external_crate(self):
        text = "use serde::Serialize;\n"
        assert _extract_rust_imports(text) == ["serde::Serialize"]

    def test_workspace_crate(self):
        text = "use my_crate::module::thing;\n"
        assert _extract_rust_imports(text) == ["my_crate::module::thing"]

    def test_multiple_imports(self):
        text = "use crate::foo;\nuse super::bar;\nuse serde::Deserialize;\n"
        result = _extract_rust_imports(text)
        assert "crate::foo" in result
        assert "super::bar" in result
        assert "serde::Deserialize" in result


class TestRustGroupedUse:
    def test_simple_grouped(self):
        text = "use crate::{foo, bar};\n"
        result = _extract_rust_imports(text)
        assert "crate::foo" in result
        assert "crate::bar" in result
        # Must NOT emit bare crate
        assert "crate" not in result

    def test_nested_grouped(self):
        text = "use crate::{foo, bar::baz};\n"
        result = _extract_rust_imports(text)
        assert "crate::foo" in result
        assert "crate::bar::baz" in result
        assert "crate" not in result

    def test_super_grouped(self):
        text = "use super::{mod_a, mod_b};\n"
        result = _extract_rust_imports(text)
        assert "super::mod_a" in result
        assert "super::mod_b" in result
        assert "super" not in result

    def test_grouped_no_bare_prefix(self):
        """Ensure grouped imports never emit bare crate/super/self."""
        text = "use crate::{alpha, beta};\n"
        result = _extract_rust_imports(text)
        for imp in result:
            assert imp != "crate"
            assert imp != "super"
            assert imp != "self"
            assert "::" in imp

    def test_grouped_does_not_emit_bare_super(self):
        text = "use super::{foo, bar};\n"
        result = _extract_rust_imports(text)
        assert "super" not in result


class TestRustCommentFiltering:
    def test_line_comment_ignored(self):
        text = "// use crate::fake;\nuse crate::real;\n"
        result = _extract_rust_imports(text)
        assert "crate::fake" not in result
        assert "crate::real" in result

    def test_line_comment_with_leading_space(self):
        text = "  // use crate::fake;\nuse crate::real;\n"
        result = _extract_rust_imports(text)
        assert "crate::fake" not in result
        assert "crate::real" in result

    def test_multiple_line_comments(self):
        text = "// use a::b;\n// use c::d;\nuse e::f;\n"
        result = _extract_rust_imports(text)
        assert result == ["e::f"]

    def test_real_use_not_in_comment(self):
        text = "use serde::Serialize;\n"
        result = _extract_rust_imports(text)
        assert "serde::Serialize" in result

    def test_mixed_comments_and_uses(self):
        text = """use crate::alpha;
// use crate::beta;
use crate::gamma;
// use crate::delta;
"""
        result = _extract_rust_imports(text)
        assert "crate::alpha" in result
        assert "crate::beta" not in result
        assert "crate::gamma" in result
        assert "crate::delta" not in result


class TestRustEdgeCases:
    def test_empty_file(self):
        assert _extract_rust_imports("") == []

    def test_only_comments(self):
        assert _extract_rust_imports("// use crate::foo;\n") == []

    def test_whitespace_only(self):
        assert _extract_rust_imports("   \n  \n") == []

    def test_use_without_semicolon_skipped(self):
        """Simple use without semicolon should not match (strict pattern)."""
        text = "use crate::foo\n"
        result = _extract_rust_imports(text)
        assert "crate::foo" not in result

    def test_grouped_with_trailing_comma(self):
        text = "use crate::{foo, bar,};\n"
        result = _extract_rust_imports(text)
        assert "crate::foo" in result
        assert "crate::bar" in result

    def test_real_world_rust_file(self):
        text = """use std::collections::HashMap;
use crate::config::Settings;
use super::handler;
use serde::{Deserialize, Serialize};

pub struct App {
    settings: Settings,
}
"""
        result = _extract_rust_imports(text)
        assert "std::collections::HashMap" in result
        assert "crate::config::Settings" in result
        assert "super::handler" in result
        assert "serde::Deserialize" in result
        assert "serde::Serialize" in result
        assert "serde" not in result
