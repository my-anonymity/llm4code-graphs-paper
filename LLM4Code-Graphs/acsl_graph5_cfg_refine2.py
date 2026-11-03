#!/usr/bin/env python3
"""Rebuild and audit CFGs for a C source dataset using Clang AST graphs.

This is a separate second-stage pass. It calls build_graph() from
acsl_graph5.py to preserve the existing AST, CALLS, DATA_DEP, and
example-input pipeline, then removes the earlier approximate CFG and rebuilds
control-flow sequencing and branch/loop edges from AST_CHILD order.

The CFG is intraprocedural and conservative. It does not execute C, prove path
feasibility, or replace a compiler's full CFG/data-flow analysis. Unusual C
constructs are reported in per-file warnings rather than presented as verified.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import networkx as nx


CFG_PREFIX = "CFG_"
LOOP_KINDS = {"FOR_STMT", "WHILE_STMT", "DO_STMT"}
TERMINATORS = {"RETURN_STMT", "BREAK_STMT", "CONTINUE_STMT", "GOTO_STMT"}
EXPR_KINDS = {
    "BINARY_OPERATOR", "UNARY_OPERATOR", "CALL_EXPR", "DECL_REF_EXPR",
    "ARRAY_SUBSCRIPT_EXPR", "MEMBER_REF_EXPR", "INTEGER_LITERAL",
    "FLOATING_LITERAL", "CHARACTER_LITERAL", "STRING_LITERAL",
    "CSTYLE_CAST_EXPR", "PAREN_EXPR", "CONDITIONAL_OPERATOR",
    "UNEXPOSED_EXPR", "CXX_BOOL_LITERAL_EXPR", "INIT_LIST_EXPR",
}


def edge_type(data: dict[str, Any]) -> str:
    return str(data.get("edge_type", ""))


def ast_children(G: nx.MultiDiGraph, node: str) -> list[str]:
    """AST children in original traversal order (ast_N edge keys)."""
    children = []
    for _, v, key, data in G.out_edges(node, keys=True, data=True):
        if edge_type(data) != "AST_CHILD":
            continue
        match = re.search(r"ast_(\d+)$", str(key))
        children.append((int(match.group(1)) if match else 10**15, v))
    return [v for _, v in sorted(children)]


def add_edge(
    G: nx.MultiDiGraph,
    source: str,
    target: str,
    kind: str,
    **attrs: Any,
) -> None:
    """Add one edge per (source, target, type), preserving MultiDiGraph format."""
    for _, dest, _, data in G.out_edges(source, keys=True, data=True):
        if dest == target and edge_type(data) == kind:
            return
    key = f"{kind}_{G.number_of_edges()}"
    G.add_edge(source, target, key=key, edge_type=kind, **attrs)


def remove_previous_cfg(G: nx.MultiDiGraph) -> None:
    """Remove existing CFG edges and old synthetic CFG nodes."""
    doomed = [
        (u, v, k)
        for u, v, k, d in G.edges(keys=True, data=True)
        if edge_type(d).startswith(CFG_PREFIX)
    ]
    G.remove_edges_from(doomed)

    for node, data in list(G.nodes(data=True)):
        if data.get("synthetic") and str(
            data.get("node_type", "")
        ).startswith("CFG_"):
            G.remove_node(node)


def synthetic_node(
    G: nx.MultiDiGraph,
    key: str,
    kind: str,
    label: str,
    source_node: str,
    **attrs: Any,
) -> str:
    """Create a uniquely named synthetic CFG node."""
    node = key
    suffix = 1
    while node in G:
        node = f"{key}::{suffix}"
        suffix += 1

    src = G.nodes[source_node]
    G.add_node(
        node,
        node_type=kind,
        label=label,
        text=label,
        line=src.get("line", 0),
        column=src.get("column", 0),
        function=src.get("function", ""),
        synthetic=True,
        **attrs,
    )
    return node


def source_text_for_graph(G: nx.MultiDiGraph) -> str | None:
    """Read the original C source, if the recorded path is accessible."""
    source_path = G.graph.get("source_file")
    if not source_path:
        return None
    try:
        return Path(str(source_path)).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None


def split_for_header(
    source: str,
    line: int,
    column: int,
) -> list[str] | None:
    """Return top-level for-header clauses when source text is available.

    Handles nested parentheses and quoted strings while locating the two
    top-level semicolons. This helps map omitted for clauses to AST children.
    """
    lines = source.splitlines(keepends=True)
    if line < 1 or line > len(lines):
        return None

    offset = sum(len(x) for x in lines[:line - 1]) + max(column - 1, 0)
    match = re.search(r"\bfor\s*\(", source[offset:])
    if not match:
        # Column locations occasionally point to the token after indentation;
        # fall back to searching the rest of this line.
        return None

    open_paren = offset + match.end() - 1
    depth = 1
    quote = None
    escaped = False
    semicolons = []
    close_paren = None
    i = open_paren + 1

    while i < len(source):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        else:
            if ch in ('"', "'"):
                quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    close_paren = i
                    break
            elif ch == ";" and depth == 1:
                semicolons.append(i)
        i += 1

    if close_paren is None or len(semicolons) != 2:
        return None

    starts = [
        open_paren + 1,
        semicolons[0] + 1,
        semicolons[1] + 1,
    ]
    ends = [semicolons[0], semicolons[1], close_paren]
    return [
        source[a:b].strip()
        for a, b in zip(starts, ends)
    ]


def for_clause_nodes(
    G: nx.MultiDiGraph,
    loop: str,
    children: list[str],
    source: str | None,
    warnings: list[str],
) -> tuple[str | None, str | None, str | None, str]:
    """Map direct FOR_STMT children to init/condition/increment/body.

    Full four-child loops are unambiguous. For omitted clauses, source header
    text is used when available. If source text is unavailable, common AST
    shapes are handled conservatively and ambiguity is recorded.
    """
    if not children:
        return None, None, None, "no_children"

    body = children[-1]
    clauses = children[:-1]
    init = condition = increment = None

    header = (
        split_for_header(
            source,
            int(G.nodes[loop].get("line", 0)),
            int(G.nodes[loop].get("column", 0)),
        )
        if source
        else None
    )

    if header is not None:
        slots = [i for i, value in enumerate(header) if value]
        if len(slots) == len(clauses):
            for slot, child in zip(slots, clauses):
                if slot == 0:
                    init = child
                elif slot == 1:
                    condition = child
                else:
                    increment = child
            return init, condition, increment, "source_header_mapped"

        warnings.append(
            f"for-loop {loop}: source/header clause count differs from "
            "AST children; using fallback mapping"
        )

    if len(children) == 4:
        init, condition, increment = (
            children[0],
            children[1],
            children[2],
        )
        return init, condition, increment, "four_child_ast_order"

    if len(children) == 3:
        first_kind = (
            str(G.nodes[clauses[0]].get("node_type", ""))
            if clauses
            else ""
        )
        second_kind = (
            str(G.nodes[clauses[1]].get("node_type", ""))
            if len(clauses) > 1
            else ""
        )

        # Declaration initializers cannot be confused with a condition.
        if first_kind == "DECL_STMT":
            init, condition = clauses[0], clauses[1]
            warnings.append(
                f"for-loop {loop}: increment-vs-condition ambiguity "
                "without readable source"
            )
        else:
            condition, increment = clauses[0], clauses[1]
            warnings.append(
                f"for-loop {loop}: init-vs-condition ambiguity "
                "without readable source"
            )

        return init, condition, increment, "two_clause_fallback"

    if len(children) == 2:
        only = clauses[0] if clauses else None
        kind = str(G.nodes[only].get("node_type", "")) if only else ""

        if kind == "DECL_STMT":
            init = only
            warnings.append(
                f"for-loop {loop}: condition/increment omitted or ambiguous; "
                "treating loop as condition-true"
            )
        else:
            condition = only
            warnings.append(
                f"for-loop {loop}: only one clause child; "
                "omitted-clause mapping is approximate"
            )

        return init, condition, increment, "one_clause_fallback"

    if clauses:
        warnings.append(
            f"for-loop {loop}: unexpected {len(children)} AST children; "
            "loop mapping is approximate"
        )

    return init, condition, increment, "fallback"
    
def rebuild_cfg(
    G: nx.MultiDiGraph,
) -> tuple[nx.MultiDiGraph, dict[str, Any]]:
    remove_previous_cfg(G)

    ast = {n: ast_children(G, n) for n in G.nodes}
    kind = lambda n: str(G.nodes[n].get("node_type", ""))
    functions = [n for n in G.nodes if kind(n) == "FUNCTION_DECL"]
    source = source_text_for_graph(G)

    audit: dict[str, Any] = {
        "functions": [],
        "loop_count": 0,
        "loop_back_edges": 0,
        "branch_edges": 0,
        "warnings": [],
    }
    loop_nodes = []

    def connect(
        incoming: list[str],
        target: str,
        role: str = "statement_sequence",
    ) -> None:
        for predecessor in incoming:
            add_edge(
                G,
                predecessor,
                target,
                "CFG_NEXT",
                role=role,
            )

    def condition_child(
        node: str,
        children: list[str],
    ) -> str | None:
        # For IF_STMT, first direct AST child is the condition expression.
        return children[0] if children else None

    def build_stmt(
        node: str,
        incoming: list[str],
        loop_stack: tuple[dict[str, Any], ...] = (),
    ) -> list[str]:
        node_kind = kind(node)
        children = ast.get(node, [])

        if node_kind == "COMPOUND_STMT":
            if incoming:
                connect(incoming, node, "compound_entry")

            exits = [node]
            for child in children:
                exits = build_stmt(child, exits, loop_stack)
            return exits

        if node_kind == "IF_STMT":
            if not children:
                connect(incoming, node)
                audit["warnings"].append(
                    f"if-statement {node} has no AST children"
                )
                return [node]

            cond = condition_child(node, children)
            branches = children[1:]

            if cond is None or not branches:
                connect(incoming, node)
                return [node]

            connect(incoming, cond, "if_condition_entry")

            join = synthetic_node(
                G,
                f"CFG_IF_JOIN::{node}",
                "CFG_IF_JOIN_NODE",
                "if-join",
                node,
                join_for=str(node),
            )

            then_exits = build_stmt(branches[0], [], loop_stack)

            add_edge(
                G,
                cond,
                branches[0],
                "CFG_TRUE",
                role="if_condition_true",
                condition_for=str(node),
            )

            if len(branches) > 1:
                else_exits = build_stmt(branches[1], [], loop_stack)

                add_edge(
                    G,
                    cond,
                    branches[1],
                    "CFG_FALSE",
                    role="if_condition_false",
                    condition_for=str(node),
                )

                for exit_node in then_exits + else_exits:
                    add_edge(
                        G,
                        exit_node,
                        join,
                        "CFG_JOIN",
                        role="if_branch_join",
                    )
            else:
                add_edge(
                    G,
                    cond,
                    join,
                    "CFG_FALSE",
                    role="if_condition_false_no_else",
                    condition_for=str(node),
                )

                for exit_node in then_exits:
                    add_edge(
                        G,
                        exit_node,
                        join,
                        "CFG_JOIN",
                        role="if_branch_join",
                    )

            audit["branch_edges"] += 2
            return [join]

        if node_kind == "FOR_STMT":
            loop_nodes.append(node)

            init, cond, increment, mapping = for_clause_nodes(
                G,
                node,
                children,
                source,
                audit["warnings"],
            )

            if not children:
                connect(incoming, node)
                return [node]

            body = children[-1]

            exit_node = synthetic_node(
                G,
                f"CFG_LOOP_EXIT_NODE::{node}",
                "CFG_LOOP_EXIT_NODE",
                "for-loop false-condition exit",
                node,
                loop_exit_for=str(node),
            )

            test = cond or node

            if init is not None:
                connect(incoming, init, "for_initializer_entry")
                add_edge(
                    G,
                    init,
                    test,
                    "CFG_NEXT",
                    role="for_initializer_to_condition",
                )
            else:
                connect(incoming, test, "for_condition_entry")

            G.nodes[node]["cfg_condition_node"] = str(test)
            G.nodes[node]["cfg_body_node"] = str(body)
            G.nodes[node]["for_clause_mapping"] = mapping
            G.nodes[node]["is_loop_header"] = True
            G.nodes[node]["loop_kind"] = node_kind

            add_edge(
                G,
                test,
                body,
                "CFG_TRUE",
                role="loop_condition_true",
                loop_header=str(node),
            )

            if cond is not None:
                add_edge(
                    G,
                    test,
                    exit_node,
                    "CFG_FALSE",
                    role="loop_condition_false",
                    loop_header=str(node),
                )
            else:
                # A missing for-condition means true. Do not create a false
                # edge to the exit: an explicit break is required to leave.
                G.nodes[exit_node]["unconditional_loop_exit"] = False

            loop_context = {
                "header": node,
                "condition": test,
                "increment": increment,
                "exit": exit_node,
                "kind": node_kind,
            }

            body_exits = build_stmt(
                body,
                [],
                loop_stack + (loop_context,),
            )

            if increment is not None:
                for exit_node_from_body in body_exits:
                    add_edge(
                        G,
                        exit_node_from_body,
                        increment,
                        "CFG_NEXT",
                        role="body_to_for_increment",
                    )

                add_edge(
                    G,
                    increment,
                    test,
                    "CFG_LOOP_BACK",
                    role="for_increment_to_condition",
                    loop_header=str(node),
                )
            else:
                for exit_node_from_body in body_exits:
                    add_edge(
                        G,
                        exit_node_from_body,
                        test,
                        "CFG_LOOP_BACK",
                        role="body_to_for_condition",
                        loop_header=str(node),
                    )

            audit["loop_count"] += 1
            audit["loop_back_edges"] += (
                1 if increment is not None or body_exits else 0
            )

            return [exit_node]

        if node_kind == "WHILE_STMT":
            loop_nodes.append(node)

            if len(children) < 2:
                connect(incoming, node)
                audit["warnings"].append(
                    f"while-loop {node} has fewer than two AST children"
                )
                return [node]

            cond, body = children[0], children[-1]

            exit_node = synthetic_node(
                G,
                f"CFG_LOOP_EXIT_NODE::{node}",
                "CFG_LOOP_EXIT_NODE",
                "while-loop false-condition exit",
                node,
                loop_exit_for=str(node),
            )

            connect(incoming, cond, "while_condition_entry")

            G.nodes[node]["cfg_condition_node"] = str(cond)
            G.nodes[node]["cfg_body_node"] = str(body)

            add_edge(
                G,
                cond,
                body,
                "CFG_TRUE",
                role="while_condition_true",
                loop_header=str(node),
            )
            add_edge(
                G,
                cond,
                exit_node,
                "CFG_FALSE",
                role="while_condition_false",
                loop_header=str(node),
            )

            context = {
                "header": node,
                "condition": cond,
                "increment": None,
                "exit": exit_node,
                "kind": node_kind,
            }

            body_exits = build_stmt(
                body,
                [],
                loop_stack + (context,),
            )

            for ex in body_exits:
                add_edge(
                    G,
                    ex,
                    cond,
                    "CFG_LOOP_BACK",
                    role="while_body_to_condition",
                    loop_header=str(node),
                )

            audit["loop_count"] += 1
            audit["loop_back_edges"] += len(body_exits)

            return [exit_node]

        if node_kind == "DO_STMT":
            loop_nodes.append(node)

            if len(children) < 2:
                connect(incoming, node)
                audit["warnings"].append(
                    f"do-while loop {node} has fewer than two AST children"
                )
                return [node]

            body, cond = children[0], children[-1]

            exit_node = synthetic_node(
                G,
                f"CFG_LOOP_EXIT_NODE::{node}",
                "CFG_LOOP_EXIT_NODE",
                "do-while false-condition exit",
                node,
                loop_exit_for=str(node),
            )

            connect(incoming, body, "do_body_entry")

            G.nodes[node]["cfg_condition_node"] = str(cond)
            G.nodes[node]["cfg_body_node"] = str(body)

            context = {
                "header": node,
                "condition": cond,
                "increment": None,
                "exit": exit_node,
                "kind": node_kind,
            }

            body_exits = build_stmt(
                body,
                [],
                loop_stack + (context,),
            )

            for ex in body_exits:
                add_edge(
                    G,
                    ex,
                    cond,
                    "CFG_NEXT",
                    role="do_body_to_condition",
                )

            add_edge(
                G,
                cond,
                body,
                "CFG_LOOP_BACK",
                role="do_condition_true_to_body",
                loop_header=str(node),
            )
            add_edge(
                G,
                cond,
                exit_node,
                "CFG_FALSE",
                role="do_condition_false",
                loop_header=str(node),
            )

            audit["loop_count"] += 1
            audit["loop_back_edges"] += 1

            return [exit_node]

        # Generic statement, including declarations, expression statements and
        # calls. AST expression children are not separately sequenced as CFG
        # statements; the statement node is the execution unit at this level.
        connect(incoming, node)

        if node_kind in TERMINATORS:
            if node_kind == "BREAK_STMT" and loop_stack:
                add_edge(
                    G,
                    node,
                    loop_stack[-1]["exit"],
                    "CFG_BREAK",
                    role="break_to_loop_exit",
                )

            elif node_kind == "CONTINUE_STMT" and loop_stack:
                context = loop_stack[-1]
                target = context["increment"] or context["condition"]

                if target:
                    add_edge(
                        G,
                        node,
                        target,
                        "CFG_CONTINUE",
                        role="continue_to_loop_latch",
                    )

            # GOTO target resolution needs label mapping and is deliberately
            # not guessed.
            elif node_kind == "GOTO_STMT":
                audit["warnings"].append(
                    f"goto statement {node}: target resolution not implemented"
                )

            return []

        return [node]

    for fn in functions:
        body = next(
            (
                c for c in ast.get(fn, [])
                if kind(c) == "COMPOUND_STMT"
            ),
            None,
        )

        if body is None:
            continue

        G.nodes[body]["cfg_role"] = "function_entry"
        normal_exits = build_stmt(body, [])

        audit["functions"].append(
            {
                "name": G.nodes[fn].get("label", ""),
                "function_node": str(fn),
                "normal_exit_nodes": [str(n) for n in normal_exits],
            }
        )

    # Parameter roles are inferred from use sites and type/AST context.
    # These are descriptive labels, not execution-derived facts.
    ast_parent = {}

    for parent, child_list in ast.items():
        for child in child_list:
            ast_parent.setdefault(child, parent)

    def ancestor_kinds(node: str) -> set[str]:
        result = set()
        current = node
        seen = set()

        while current in ast_parent and current not in seen:
            seen.add(current)
            current = ast_parent[current]
            result.add(kind(current))

        return result

    for fn in functions:
        descendants = set()
        stack = [fn]

        while stack:
            current = stack.pop()
            if current in descendants:
                continue
            descendants.add(current)
            stack.extend(ast.get(current, []))

        params = [
            p for p in ast.get(fn, [])
            if kind(p) == "PARM_DECL"
        ]

        for param in params:
            name = str(G.nodes[param].get("label", ""))

            refs = [
                r for r in descendants
                if kind(r) == "DECL_REF_EXPR"
                and str(G.nodes[r].get("label", "")) == name
            ]

            lines = sorted(
                {
                    int(G.nodes[r].get("line", 0))
                    for r in refs
                }
            )

            roles = set()
            evidence = []
            param_type = str(G.nodes[param].get("c_type", ""))

            for ref in refs:
                parent = next(
                    (
                        u for u, _, _, d
                        in G.in_edges(ref, keys=True, data=True)
                        if edge_type(d) == "AST_CHILD"
                    ),
                    None,
                )

                parent_kind = kind(parent) if parent else ""
                ancestors = ancestor_kinds(ref)

                if (
                    parent_kind == "ARRAY_SUBSCRIPT_EXPR"
                    or "ARRAY_SUBSCRIPT_EXPR" in ancestors
                ):
                    roles.add("array_index_or_buffer_access")
                    evidence.append(
                        "used in an array-subscript expression"
                    )

                if parent_kind in {"BINARY_OPERATOR", "UNARY_OPERATOR"}:
                    roles.add("expression_operand")

                # A use in a loop condition is identified below from
                # condition ASTs.

            if "*" in param_type or "[" in param_type:
                roles.add("pointer_or_array_input")

            if (
                name.lower() in {
                    "arr", "array", "buffer", "data", "values"
                }
                and any(
                    "ARRAY_SUBSCRIPT_EXPR" in ancestor_kinds(ref)
                    for ref in refs
                )
            ):
                roles.add("array_data_or_buffer")

            for loop in loop_nodes:
                condition_id = G.nodes[loop].get("cfg_condition_node")

                if condition_id and condition_id in descendants:
                    cond_desc = set()
                    todo = [str(condition_id)]

                    while todo:
                        x = todo.pop()
                        if x in cond_desc:
                            continue
                        cond_desc.add(x)
                        todo.extend(ast.get(x, []))

                    if any(r in cond_desc for r in refs):
                        roles.add("loop_bound_or_control_input")
                        evidence.append(
                            "used in loop condition at line "
                            f"{G.nodes[loop].get('line', 0)}"
                        )

            if not roles:
                roles.add("input_parameter")
                evidence.append(
                    "referenced in the function body"
                    if refs
                    else "no matching body reference found"
                )

            # Familiar descriptive roles are secondary hints. These names
            # do not replace the usage-derived evidence.
            if name.lower() in {"low", "min", "start", "begin"}:
                roles.add("lower_bound_or_start_index")

            if name.lower() in {
                "high", "max", "end", "limit", "n", "len", "length"
            }:
                roles.add("upper_bound_or_size_limit")

            G.nodes[param]["input_role"] = ";".join(sorted(roles))
            G.nodes[param]["input_roles_json"] = json.dumps(sorted(roles))
            G.nodes[param]["input_role_evidence"] = "; ".join(
                sorted(set(evidence))
            )
            G.nodes[param]["reference_lines"] = json.dumps(lines)
            G.nodes[param]["reference_count"] = len(refs)

    # Link parameters to loop headers only when their references occur in
    # the loop condition. This is a structural input-control hint, not proof
    # of path feasibility.
    for loop in loop_nodes:
        condition_id = G.nodes[loop].get("cfg_condition_node")

        if not condition_id or condition_id not in G:
            continue

        condition_desc = set()
        todo = [str(condition_id)]

        while todo:
            current = todo.pop()
            if current in condition_desc:
                continue
            condition_desc.add(current)
            todo.extend(ast.get(current, []))

        refs_by_function: dict[str, dict[str, str]] = {}

        for n, data in G.nodes(data=True):
            if kind(n) == "PARM_DECL":
                refs_by_function.setdefault(
                    str(data.get("function", "")), {}
                )[str(data.get("label", ""))] = n

        fn_name = str(G.nodes[loop].get("function", ""))

        for ref in condition_desc:
            if kind(ref) != "DECL_REF_EXPR":
                continue

            pname = str(G.nodes[ref].get("label", ""))
            pnode = refs_by_function.get(fn_name, {}).get(pname)

            if pnode:
                add_edge(
                    G,
                    pnode,
                    loop,
                    "INPUT_CONTROLS",
                    parameter=pname,
                    condition_node=str(condition_id),
                    semantics=(
                        "parameter referenced in loop-condition AST; "
                        "no path evaluation"
                    ),
                )

    counts: dict[str, int] = {}

    for _, _, data in G.edges(data=True):
        et = edge_type(data)
        if et.startswith(CFG_PREFIX):
            counts[et] = counts.get(et, 0) + 1

    audit["cfg_edge_counts"] = counts
    audit["loop_count"] = len(loop_nodes)
    audit["loop_back_edges"] = counts.get("CFG_LOOP_BACK", 0)

    audit["input_control_edges"] = sum(
        1 for _, _, d in G.edges(data=True)
        if edge_type(d) == "INPUT_CONTROLS"
    )

    audit["data_dependency_edges"] = sum(
        1 for _, _, d in G.edges(data=True)
        if edge_type(d) == "DATA_DEP"
    )

    audit["input_parameters"] = [
        {
            "function": d.get("function", ""),
            "name": d.get("label", ""),
            "roles": d.get("input_roles_json", "[]"),
            "evidence": d.get("input_role_evidence", ""),
            "reference_lines": d.get("reference_lines", "[]"),
        }
        for _, d in G.nodes(data=True)
        if d.get("node_type") == "PARM_DECL"
    ]

    G.graph["graph_semantics"] = (
        "AST + CFG rebuilt from AST_CHILD sequencing and branches; "
        "loop false exits explicit; DATA_DEP remains a conservative "
        "name-based hint; INPUT_CONTROLS marks condition references, "
        "not path feasibility"
    )

    G.graph["refinement_stage"] = "acsl_graph5_cfg_refine2.py"
    G.graph["cfg_edge_counts_json"] = json.dumps(counts, sort_keys=True)
    G.graph["loop_header_count"] = len(loop_nodes)
    G.graph["data_dependency_edge_count"] = audit["data_dependency_edges"]
    G.graph["input_control_edge_count"] = audit["input_control_edges"]

    return G, audit
    
def process_source(
    source: Path,
    output_graph: Path,
    input_output: Path,
    report_output: Path,
    clang_args: list[str],
) -> dict[str, Any]:
    from acsl_graph5 import build_graph

    G, examples, _tu = build_graph(source, clang_args)
    G, audit = rebuild_cfg(G)

    output_graph.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, output_graph)

    input_output.parent.mkdir(parents=True, exist_ok=True)
    input_output.write_text(
        json.dumps(
            {
                "source": str(source),
                "functions": examples,
                "note": (
                    "Example inputs are deterministic templates, not "
                    "guaranteed-valid executions; validate preconditions, "
                    "pointer lengths, and array bounds."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )

    return audit


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild CFGs for a C dataset into a separate output tree."
        )
    )

    parser.add_argument(
        "--input-dir",
        default="acsl_CFiles-Exp3",
        help="Root directory containing C source files",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output root (default: INPUT_DIR/graphs_cfg_refined)",
    )
    parser.add_argument(
        "--libclang",
        default=None,
        help="Explicit libclang shared-library path",
    )
    parser.add_argument(
        "--clang-arg",
        action="append",
        default=[],
        help="Extra Clang argument; repeat for include paths",
    )
    parser.add_argument(
        "--skip-dir",
        action="append",
        default=[],
        help="Directory name to skip; may be repeated",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Optional pilot limit; 0 means all files",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()

    if not input_dir.is_dir():
        raise SystemExit(
            f"Input directory does not exist: {input_dir}"
        )

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else input_dir / "graphs_cfg_refined"
    )

    skip_names = {
        "graphs",
        "graphs_refined",
        "graphs_cfg_refined",
        "embeddings",
        "__pycache__",
        ".venv",
    } | set(args.skip_dir)

    from acsl_graph5 import configure_clang

    configure_clang(args.libclang)

    report_dir = output_dir / "reports"
    input_dir_output = output_dir / "inputs"

    summary: dict[str, Any] = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "files_discovered": 0,
        "files_processed": 0,
        "files_failed": 0,
        "loop_count": 0,
        "loop_back_edges": 0,
        "cfg_edge_counts": {},
        "data_dependency_edges": 0,
        "input_control_edges": 0,
        "warnings_count": 0,
        "errors": [],
        "warnings": [],
    }

    sources = []

    for root, dirs, files in os.walk(input_dir):
        dirs[:] = [
            d for d in dirs
            if d not in skip_names
        ]

        for filename in sorted(files):
            if filename.lower().endswith(".c"):
                sources.append(Path(root) / filename)

    sources.sort()

    if args.max_files > 0:
        sources = sources[:args.max_files]

    summary["files_discovered"] = len(sources)

    for source in sources:
        rel = source.relative_to(input_dir)

        print(
            f"[{summary['files_processed'] + summary['files_failed'] + 1}"
            f"/{len(sources)}] {rel}"
        )

        graph_out = output_dir / (str(rel) + ".graphml")
        inputs_out = input_dir_output / (str(rel) + ".json")
        report_out = report_dir / (str(rel) + ".json")

        try:
            audit = process_source(
                source,
                graph_out,
                inputs_out,
                report_out,
                args.clang_arg,
            )

            summary["files_processed"] += 1
            summary["loop_count"] += audit.get("loop_count", 0)
            summary["loop_back_edges"] += audit.get(
                "loop_back_edges", 0
            )
            summary["data_dependency_edges"] += audit.get(
                "data_dependency_edges", 0
            )
            summary["input_control_edges"] += audit.get(
                "input_control_edges", 0
            )
            summary["warnings_count"] += len(
                audit.get("warnings", [])
            )

            for edge_name, count in audit.get(
                "cfg_edge_counts", {}
            ).items():
                summary["cfg_edge_counts"][edge_name] = (
                    summary["cfg_edge_counts"].get(edge_name, 0)
                    + count
                )

            if audit.get("warnings"):
                summary["warnings"].append(
                    {
                        "file": str(rel),
                        "warnings": audit["warnings"],
                    }
                )

            print(
                f"  OK: loops={audit.get('loop_count', 0)}, "
                f"back_edges={audit.get('loop_back_edges', 0)}, "
                f"warnings={len(audit.get('warnings', []))}"
            )

        except Exception as exc:
            summary["files_failed"] += 1
            summary["errors"].append(
                {
                    "file": str(rel),
                    "error": str(exc),
                }
            )
            print(f"  ERROR: {exc}")

    report_dir.mkdir(parents=True, exist_ok=True)

    (report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nCFG refinement finished.")
    print(
        f"Discovered: {summary['files_discovered']}; "
        f"processed: {summary['files_processed']}; "
        f"failed: {summary['files_failed']}"
    )
    print(
        f"Loops: {summary['loop_count']}; "
        f"loop-back edges: {summary['loop_back_edges']}; "
        f"warnings: {summary['warnings_count']}"
    )
    print(f"Output graphs: {output_dir}")
    print(f"Summary: {report_dir / 'summary.json'}")
    print(
        "Note: this is an AST-derived conservative CFG; "
        "it does not execute code or prove path feasibility."
    )


if __name__ == "__main__":
    main()

