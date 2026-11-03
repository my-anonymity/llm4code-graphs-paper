#!/usr/bin/env python3
"""
Build richer C function graphs from Clang ASTs.

Each GraphML file contains:
  * AST_CHILD edges: complete syntactic hierarchy
  * CFG_* edges: approximate intraprocedural control flow (branches, loops,
    returns, break/continue)
  * CALLS edges: direct function-call relationships
  * DATA_DEP edges: conservative name-based read/write relationships

Concrete parameter examples are written to inputs/*.json and attached to
parameter nodes. They document usable sample inputs; they do not execute the
C program or guarantee that every path is feasible. For path coverage, compile
and run the C functions with a test harness/fuzzer.
"""
import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict

import networkx as nx
import numpy as np
from clang.cindex import Index, Config, CursorKind, TypeKind
from sentence_transformers import SentenceTransformer

# Override with --libclang or LIBCLANG_PATH if your installation differs.
# Prefer the libclang bundled with the Python package; allow an explicit override.
try:
    import clang.cindex as _clang_cindex
    _bundled_libclang = Path(_clang_cindex.__file__).parent / "native" / "libclang.so"
    DEFAULT_LIBCLANG = str(_bundled_libclang) if _bundled_libclang.exists() else "/usr/lib/llvm-17/lib/libclang.so"
except Exception:
    DEFAULT_LIBCLANG = "/usr/lib/llvm-17/lib/libclang.so"

def configure_clang(path=None):
    lib = path or os.environ.get("LIBCLANG_PATH") or DEFAULT_LIBCLANG
    if not lib or not os.path.isfile(lib):
        raise FileNotFoundError(
            f"LibClang library not found: {lib}. Install the bundled library with "
            "`python -m pip install --upgrade libclang`, or pass --libclang /path/to/libclang.so."
        )
    Config.set_library_file(lib)

def safe_type(t):
    try:
        return t.spelling or "unknown"
    except Exception:
        return "unknown"

def concrete_value_for_type(t, array_len=4):
    """Return a deterministic, JSON-serializable example for a C parameter."""
    spelling = safe_type(t)
    kind = t.kind
    if kind == TypeKind.CONSTANTARRAY:
        try:
            n = max(1, min(int(t.element_count), 16))
        except Exception:
            n = array_len
        return [concrete_value_for_type(t.element_type) for _ in range(n)]
    if kind in (TypeKind.INCOMPLETEARRAY, TypeKind.VARIABLEARRAY):
        return [concrete_value_for_type(t.element_type) for _ in range(array_len)]
    if kind in (TypeKind.POINTER,):
        # A concrete example for pointer-like inputs is represented as a buffer.
        try:
            pointee = t.get_pointee()
            if pointee.kind == TypeKind.CHAR_S:
                return "sample"
            if pointee.kind in (TypeKind.CONSTANTARRAY, TypeKind.INCOMPLETEARRAY):
                return [concrete_value_for_type(pointee.element_type) for _ in range(array_len)]
            return [concrete_value_for_type(pointee) for _ in range(array_len)]
        except Exception:
            return [0, 1, 2, 3]
    if kind == TypeKind.BOOL:
        return True
    if kind in (TypeKind.CHAR_S, TypeKind.SCHAR, TypeKind.UCHAR):
        return "A"
    if kind in (TypeKind.FLOAT, TypeKind.DOUBLE, TypeKind.LONGDOUBLE):
        return 1.0
    if kind in (TypeKind.VOID,):
        return None
    if kind in (TypeKind.RECORD,):
        return {"example": 0, "_note": "replace with fields valid for this struct"}
    if kind in (TypeKind.ENUM,):
        return 0
    if kind in (TypeKind.INT, TypeKind.UINT, TypeKind.LONG, TypeKind.ULONG,
                TypeKind.LONGLONG, TypeKind.ULONGLONG, TypeKind.SHORT,
                TypeKind.USHORT, TypeKind.INT128, TypeKind.UINT128):
        return 1
    if "*" in spelling:
        return [0, 1, 2, 3]
    return 0

def node_location(cursor):
    loc = cursor.location
    return int(loc.line or 0), int(loc.column or 0)

def build_graph(file_path, clang_args=None):
    index = Index.create()
    tu = index.parse(str(file_path), args=clang_args or [])
    errors = [d for d in tu.diagnostics if d.severity >= 3]
    if errors:
        raise RuntimeError("Clang parse error(s): " + "; ".join(str(d) for d in errors))

    G = nx.MultiDiGraph()
    source = Path(file_path).resolve()
    file_node = "FILE::" + Path(file_path).name
    G.add_node(file_node, node_type="file", label=Path(file_path).name,
               text=Path(file_path).name, line=0, column=0)

    cursor_nodes = {}
    function_nodes = {}
    param_examples = {}
    call_edges = []
    data_records = []

    # Keep only cursors originating in this source file (not included headers).
    def from_file(cur):
        try:
            return Path(cur.location.file.name).resolve() == source
        except Exception:
            return False

    def ast_visit(cur, parent=None, function_name=None):
        if cur.kind == CursorKind.TRANSLATION_UNIT:
            uid = file_node
        else:
            line, col = node_location(cur)
            # Cursor identity is unique within this traversal; location and ordinal
            # make stable, readable IDs without Python's process-specific id().
            uid = f"AST::{cur.kind.name}::{line}:{col}::{len(cursor_nodes)}"
            label = cur.spelling or cur.displayname or cur.kind.name
            G.add_node(uid, node_type=cur.kind.name, label=label, text=label,
                       c_type=safe_type(cur.type), line=line, column=col,
                       function=function_name or "")
            cursor_nodes[cur.hash] = uid
            if parent:
                G.add_edge(parent, uid, key=f"ast_{len(G.edges)}", edge_type="AST_CHILD")
            if cur.kind == CursorKind.FUNCTION_DECL and cur.is_definition():
                function_name = cur.spelling
                G.nodes[uid]["function"] = function_name
                function_nodes[function_name] = uid
            if cur.kind == CursorKind.PARM_DECL and function_name:
                val = concrete_value_for_type(cur.type)
                G.nodes[uid]["example_value"] = json.dumps(val)
                param_examples.setdefault(function_name, {})[cur.spelling or f"arg{len(param_examples.get(function_name, {}))}"] = {
                    "c_type": safe_type(cur.type), "example": val
                }
            if cur.kind == CursorKind.CALL_EXPR:
                referenced = cur.referenced
                if referenced and referenced.spelling:
                    call_edges.append((uid, referenced.spelling))
            # Conservative identifier-based read/write hints.
            if cur.kind in (CursorKind.DECL_REF_EXPR, CursorKind.MEMBER_REF_EXPR):
                data_records.append((uid, cur.spelling, function_name, cur.kind.name))
        # Translation unit children can include headers; filter those out.
        for child in cur.get_children():
            if child.kind != CursorKind.TRANSLATION_UNIT and not from_file(child):
                continue
            ast_visit(child, uid, function_name)
        return uid

    ast_visit(tu.cursor)

    # Build an intraprocedural control-flow approximation over statement AST nodes.
    # Nodes remain linked to the AST, while CFG edges show execution ordering.
    stmt_kinds = {
        "COMPOUND_STMT", "DECL_STMT", "IF_STMT", "FOR_STMT", "WHILE_STMT",
        "DO_STMT", "SWITCH_STMT", "CASE_STMT", "DEFAULT_STMT", "RETURN_STMT",
        "BREAK_STMT", "CONTINUE_STMT", "GOTO_STMT", "LABEL_STMT",
        "NULL_STMT", "CALL_EXPR", "BINARY_OPERATOR", "UNARY_OPERATOR"
    }
    stmt_for_cursor = {}
    # Cursor objects are not retained above, so walk again and map by source location.
    def collect_statements(cur, function_name=None):
        if cur.kind == CursorKind.FUNCTION_DECL and cur.is_definition():
            function_name = cur.spelling
        if cur.kind.name in stmt_kinds and from_file(cur):
            line, col = node_location(cur)
            candidates = [uid for uid, attrs in G.nodes(data=True)
                          if attrs.get("node_type") == cur.kind.name
                          and attrs.get("line") == line and attrs.get("column") == col
                          and attrs.get("function") == (function_name or "")]
            if candidates:
                stmt_for_cursor[id(cur)] = candidates[0]
        for child in cur.get_children():
            if child.kind != CursorKind.TRANSLATION_UNIT and not from_file(child):
                continue
            collect_statements(child, function_name)
    collect_statements(tu.cursor)

    def ast_uid(cur):
        # Use the exact cursor mapping created during AST traversal first. This
        # avoids accidentally connecting a CFG edge to another node that shares
        # the same kind and source location (common with nested expressions).
        uid = cursor_nodes.get(cur.hash)
        if uid is not None:
            return uid
        line, col = node_location(cur)
        candidates = [uid for uid, attrs in G.nodes(data=True)
                      if attrs.get("node_type") == cur.kind.name
                      and attrs.get("line") == line and attrs.get("column") == col]
        return candidates[-1] if candidates else None

    def add_cfg(a, b, typ="CFG_NEXT"):
        if a and b:
            G.add_edge(a, b, key=f"{typ}_{len(G.edges)}", edge_type=typ)

    def children(cur):
        return [c for c in cur.get_children()
                if c.kind == CursorKind.TRANSLATION_UNIT or from_file(c)]

    def build_seq(items, incoming, loop_ctx=None):
        exits = list(incoming)
        for item in items:
            exits = build_stmt(item, exits, loop_ctx)
        return exits

    def build_stmt(cur, incoming, loop_ctx=None):
        k = cur.kind.name
        uid = ast_uid(cur)
        if uid is None:
            return incoming
        for prev in incoming:
            add_cfg(prev, uid)
        if k == "COMPOUND_STMT":
            return build_seq(children(cur), [uid], loop_ctx)
        if k == "IF_STMT":
            ch = children(cur)
            # Clang children are condition, then, optional else.
            if len(ch) < 2:
                return [uid]
            cond = ch[0]
            then_node = ch[1]
            else_node = ch[2] if len(ch) > 2 else None
            t_uid = ast_uid(then_node)
            e_uid = ast_uid(else_node) if else_node else None
            if t_uid: add_cfg(uid, t_uid, "CFG_TRUE")
            t_exits = build_stmt(then_node, [], loop_ctx)
            if else_node:
                if e_uid: add_cfg(uid, e_uid, "CFG_FALSE")
                e_exits = build_stmt(else_node, [], loop_ctx)
            else:
                e_exits = [uid]
            return t_exits + e_exits
        if k in ("WHILE_STMT", "FOR_STMT", "DO_STMT"):
            ch = children(cur)
            # Clang places the loop body last for these statement kinds.
            # Keep the AST loop statement as the CFG header and add explicit,
            # easily searchable loop edges so the repetition is visible in GraphML.
            body = ch[-1] if ch else None
            body_uid = ast_uid(body) if body else None
            G.nodes[uid]["is_loop_header"] = True
            G.nodes[uid]["loop_kind"] = k
            if body_uid:
                add_cfg(uid, body_uid, "CFG_LOOP_ENTER")
                add_cfg(uid, body_uid, "CFG_LOOP_BODY")
            ctx = {"continue": uid, "breaks": []}
            body_exits = build_stmt(body, [], ctx) if body else []
            for ex in body_exits:
                add_cfg(ex, uid, "CFG_LOOP_BACK")
            # Add a distinct exit node rather than a self-edge, so graph viewers
            # can display a clear loop-exit branch. The edge is structural; actual
            # feasibility depends on the condition and concrete inputs.
            exit_uid = f"CFG_LOOP_EXIT_NODE::{uid}"
            if exit_uid not in G:
                G.add_node(exit_uid, node_type="CFG_LOOP_EXIT_NODE",
                           label=f"exit {k.lower()}", text=f"exit {k.lower()}",
                           line=G.nodes[uid].get("line", 0),
                           column=G.nodes[uid].get("column", 0),
                           function=G.nodes[uid].get("function", ""),
                           loop_exit_for=uid)
            add_cfg(uid, exit_uid, "CFG_LOOP_EXIT")
            return [exit_uid] + ctx["breaks"]
        if k == "SWITCH_STMT":
            ch = children(cur)
            body = ch[-1] if len(ch) > 1 else None
            if body:
                b_uid = ast_uid(body)
                if b_uid: add_cfg(uid, b_uid, "CFG_SWITCH")
                return build_stmt(body, [], loop_ctx)
            return [uid]
        if k in ("CASE_STMT", "DEFAULT_STMT", "LABEL_STMT"):
            exits = [uid]
            for child in children(cur):
                if child.kind.name in stmt_kinds or child.kind.name == "COMPOUND_STMT":
                    exits = build_stmt(child, exits, loop_ctx)
            return exits
        if k == "RETURN_STMT":
            return []
        if k == "BREAK_STMT":
            if loop_ctx is not None:
                loop_ctx["breaks"].append(uid)
            return []
        if k == "CONTINUE_STMT":
            if loop_ctx and loop_ctx.get("continue"):
                add_cfg(uid, loop_ctx["continue"], "CFG_CONTINUE")
            return []
        if k == "GOTO_STMT":
            return []
        return [uid]

    def process_functions(cur, function_name=None):
        if cur.kind == CursorKind.FUNCTION_DECL and cur.is_definition():
            function_name = cur.spelling
            body = next((c for c in children(cur) if c.kind == CursorKind.COMPOUND_STMT), None)
            if body:
                entry = ast_uid(body)
                if entry:
                    G.nodes[entry]["cfg_role"] = "function_entry"
                    build_stmt(body, [], None)
        for child in cur.get_children():
            if child.kind != CursorKind.TRANSLATION_UNIT and not from_file(child):
                continue
            process_functions(child, function_name)
    process_functions(tu.cursor)

    # Add direct call edges after all function declarations have been collected.
    for call_uid, target_name in call_edges:
        target = function_nodes.get(target_name)
        if target:
            G.add_edge(call_uid, target, key=f"CALLS_{len(G.edges)}", edge_type="CALLS")

    # Name-based dependency hints: connect prior writes/declarations to later uses.
    # This is deliberately conservative, not a substitute for compiler dataflow analysis.
    by_func_name = defaultdict(list)
    for uid, name, fn, kind in data_records:
        if name and fn:
            by_func_name[(fn, name)].append(uid)
    for (fn, name), uids in by_func_name.items():
        for a, b in zip(uids, uids[1:]):
            if a != b:
                G.add_edge(a, b, key=f"DATA_DEP_{len(G.edges)}", edge_type="DATA_DEP")

    loop_node_count = sum(1 for _, d in G.nodes(data=True) if d.get("is_loop_header"))
    loop_edge_types = {"CFG_LOOP_ENTER", "CFG_LOOP_BODY", "CFG_LOOP_BACK", "CFG_CONTINUE", "CFG_LOOP_EXIT"}
    loop_edge_count = sum(1 for _, _, d in G.edges(data=True) if d.get("edge_type") in loop_edge_types)
    G.graph["source_file"] = str(file_path)
    G.graph["graph_semantics"] = "AST + approximate CFG with explicit loop edges + direct calls + name-based data-dependency hints"
    G.graph["loop_header_count"] = loop_node_count
    G.graph["loop_edge_count"] = loop_edge_count
    return G, param_examples, tu

def graph_to_text(G):
    parts = []
    for _, d in G.nodes(data=True):
        parts.append(f"{d.get('node_type','')} {d.get('label','')} {d.get('c_type','')}")
    for _, _, d in G.edges(data=True):
        parts.append(d.get("edge_type", ""))
    return " ".join(p for p in parts if p)

def cosine_similarity(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0

def main():
    parser = argparse.ArgumentParser(description="Create AST/CFG-rich graphs for C functions.")
    parser.add_argument("--input-dir", default="acsl_CFiles-Exp5")
    parser.add_argument("--graph-dir", default=None)
    parser.add_argument("--embedding-dir", default=None)
    parser.add_argument("--matches-file", default=None)
    parser.add_argument("--libclang", default=None)
    parser.add_argument("--clang-arg", action="append", default=[],
                        help="Extra Clang parse argument; repeat as needed, e.g. --clang-arg=-Iinclude")
    parser.add_argument("--no-embeddings", action="store_true")
    args = parser.parse_args()

    configure_clang(args.libclang)
    input_dir = Path(args.input_dir).resolve()
    graph_dir = Path(args.graph_dir or input_dir / "graphs")
    embedding_dir = Path(args.embedding_dir or input_dir / "embeddings")
    input_dir.mkdir(parents=True, exist_ok=True)
    graph_dir.mkdir(parents=True, exist_ok=True)
    embedding_dir.mkdir(parents=True, exist_ok=True)
    input_dir_abs = str(input_dir)
    matches_file = Path(args.matches_file or input_dir / "matches.json")
    inputs_dir = graph_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    model = None if args.no_embeddings else SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings, paths = [], []
    for root, dirs, files in os.walk(input_dir):
        # Do not reprocess generated output directories.
        dirs[:] = [d for d in dirs if d not in {"graphs", "embeddings", "__pycache__"}]
        for fname in sorted(files):
            if not fname.endswith(".c"):
                continue
            fpath = Path(root) / fname
            print(f"Processing: {fpath}")
            try:
                G, examples, tu = build_graph(fpath, args.clang_arg)
                rel = fpath.resolve().relative_to(input_dir)
                out = graph_dir / (str(rel) + ".graphml")
                out.parent.mkdir(parents=True, exist_ok=True)
                nx.write_graphml(G, out)
                loop_nodes = sum(1 for _, d in G.nodes(data=True) if d.get("is_loop_header"))
                loop_edges = sum(1 for _, _, d in G.edges(data=True)
                                 if d.get("edge_type") in {"CFG_LOOP_ENTER", "CFG_LOOP_BODY", "CFG_LOOP_BACK", "CFG_CONTINUE", "CFG_LOOP_EXIT"})
                print(f"  nodes={G.number_of_nodes()} edges={G.number_of_edges()} loops={loop_nodes} loop_edges={loop_edges} -> {out}")

                input_out = inputs_dir / (str(rel) + ".json")
                input_out.parent.mkdir(parents=True, exist_ok=True)
                with input_out.open("w", encoding="utf-8") as f:
                    json.dump({"source": str(rel), "functions": examples,
                               "note": "Deterministic example values only; validate pointer lengths, constraints, and preconditions before execution."},
                              f, indent=2)

                if model:
                    emb = model.encode(graph_to_text(G))
                    emb = [float(x) for x in emb]
                    emb_out = embedding_dir / (str(rel) + ".json")
                    emb_out.parent.mkdir(parents=True, exist_ok=True)
                    emb_out.write_text(json.dumps(emb, indent=2), encoding="utf-8")
                    embeddings.append(emb)
                    paths.append(str(rel))
            except Exception as exc:
                print(f"  ERROR: {exc}")

    if model:
        matches = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                matches.append({"file1": paths[i], "file2": paths[j],
                                "similarity": cosine_similarity(embeddings[i], embeddings[j])})
        matches_file.parent.mkdir(parents=True, exist_ok=True)
        matches_file.write_text(json.dumps(matches, indent=2), encoding="utf-8")
        print(f"Saved {len(matches)} similarity pairs to {matches_file}")
    print("Done. Graphs include AST hierarchy, explicit loop headers/edges, approximate control flow, and call/data edges.")
    print("Important: CFG is a structural approximation; test harnesses or symbolic execution are needed for concrete path coverage.")

if __name__ == "__main__":
    main()
