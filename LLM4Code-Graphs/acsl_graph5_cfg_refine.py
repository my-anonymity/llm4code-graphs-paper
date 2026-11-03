#!/usr/bin/env python3
"""Second-stage refinement and validation for graphs produced by acsl_graph3_loopfix.py.

This script deliberately leaves the original generator untouched. It rebuilds each
source graph, then refines loop annotations/edges and adds conservative links from
concrete parameter examples to loops whose AST refers to those parameters.

Important limits:
- CFG edges are a structural approximation, not a verified compiler CFG.
- INPUT_CONTROLS means a parameter occurs in the loop's AST; it does not mean the
  script has evaluated the condition or proved that a path is feasible.
- DATA_DEP remains a conservative name-based hint, not reaching-definitions analysis.
- No C code is compiled or executed.
"""
import argparse
import json
import os
import re
from pathlib import Path

import networkx as nx

from acsl_graph5 import configure_clang, build_graph

LOOP_KINDS = {"FOR_STMT", "WHILE_STMT", "DO_STMT"}
REBUILT_LOOP_EDGE_TYPES = {
    "CFG_LOOP_ENTER", "CFG_LOOP_BODY", "CFG_LOOP_BACK", "CFG_LOOP_EXIT"
}
LOOP_EDGE_TYPES = REBUILT_LOOP_EDGE_TYPES | {"CFG_CONTINUE"}
TERMINATING_KINDS = {"BREAK_STMT", "CONTINUE_STMT", "RETURN_STMT", "GOTO_STMT"}


def edge_type(data):
    return data.get("edge_type", "")


def ast_children(G, node):
    """Return AST children in insertion order, using generated AST edge keys."""
    edges = []
    for u, v, key, data in G.out_edges(node, keys=True, data=True):
        if edge_type(data) == "AST_CHILD":
            edges.append((str(key), v))
    def order(item):
        m = re.search(r"ast_(\d+)$", item[0])
        return int(m.group(1)) if m else 10**12
    return [v for _, v in sorted(edges, key=order)]


def descendants(G, root):
    found, stack = set(), list(ast_children(G, root))
    while stack:
        node = stack.pop()
        if node in found:
            continue
        found.add(node)
        stack.extend(ast_children(G, node))
    return found


def add_edge_once(G, source, target, typ, **attrs):
    for _, v, data in G.out_edges(source, data=True):
        if v == target and edge_type(data) == typ:
            return
    key = f"{typ}_{G.number_of_edges()}"
    G.add_edge(source, target, key=key, edge_type=typ, **attrs)


def remove_edge_types(G, types):
    remove = []
    for u, v, k, data in G.edges(keys=True, data=True):
        if edge_type(data) in types:
            remove.append((u, v, k))
    for edge in remove:
        G.remove_edge(*edge)


def enrich_graph(G, source_path, example_data):
    # Rebuild the loop-specific edges rather than trusting potentially incorrect
    # body selection in the first-stage approximate CFG (notably for do-while).
    remove_edge_types(G, REBUILT_LOOP_EDGE_TYPES)
    # Keep existing synthetic exit nodes: the first-stage graph may already have
    # CFG_NEXT edges leaving them to subsequent statements. Removing them would
    # disconnect those statements. Their loop edges are rebuilt below.

    loops = [n for n, d in G.nodes(data=True)
             if d.get("node_type") in LOOP_KINDS]
    loops.sort(key=lambda n: (int(G.nodes[n].get("line", 0)),
                              int(G.nodes[n].get("column", 0))))

    # Clear and recalculate loop-membership attributes.
    for n, d in G.nodes(data=True):
        for attr in ("loop_body_member", "loop_depth", "enclosing_loop_headers"):
            d.pop(attr, None)

    loop_info = {}
    for loop in loops:
        kind = G.nodes[loop].get("node_type", "")
        children = ast_children(G, loop)
        if not children:
            G.nodes[loop]["loop_body_selection_warning"] = "No AST children found"
            continue
        # Clang's DO_STMT children are body then condition; FOR/WHILE bodies are
        # the last child. This is intentionally handled separately.
        body = children[0] if kind == "DO_STMT" else children[-1]
        body_desc = descendants(G, body) | {body}
        loop_desc = descendants(G, loop)
        # Include synthetic exits of nested loops in the enclosing body's CFG
        # region. They are not AST descendants, but represent continuation after
        # the nested loop and may be the outer loop's final body exit.
        for nested in loops:
            if nested in body_desc:
                nested_exit = f"CFG_LOOP_EXIT_NODE::{nested}"
                if nested_exit in G:
                    body_desc.add(nested_exit)
        loop_info[loop] = {"kind": kind, "body": body, "body_nodes": body_desc,
                           "all_descendants": loop_desc}
        G.nodes[loop]["is_loop_header"] = True
        G.nodes[loop]["loop_kind"] = kind
        G.nodes[loop]["loop_body_node"] = str(body)
        G.nodes[body]["is_loop_body_root"] = True
        add_edge_once(G, loop, body, "CFG_LOOP_ENTER", semantics="structural_approximation")
        add_edge_once(G, loop, body, "CFG_LOOP_BODY", semantics="structural_approximation")

        exit_node = f"CFG_LOOP_EXIT_NODE::{loop}"
        if exit_node not in G:
            G.add_node(exit_node, node_type="CFG_LOOP_EXIT_NODE",
                       label=f"exit {kind.lower()}", text=f"exit {kind.lower()}",
                       line=G.nodes[loop].get("line", 0),
                       column=G.nodes[loop].get("column", 0),
                       function=G.nodes[loop].get("function", ""),
                       loop_exit_for=str(loop), synthetic=True)
        add_edge_once(G, loop, exit_node, "CFG_LOOP_EXIT",
                      semantics="possible_condition_false_or_loop_exit")

        # Find body terminals using the current intra-body CFG. Returns, breaks,
        # and continues do not take the ordinary loop-back edge.
        nested_body_nodes = set()
        for nested in loops:
            if nested == loop or nested not in body_desc:
                continue
            nested_kind = G.nodes[nested].get("node_type", "")
            nested_children = ast_children(G, nested)
            if nested_children:
                nested_body = nested_children[0] if nested_kind == "DO_STMT" else nested_children[-1]
                nested_body_nodes |= descendants(G, nested_body) | {nested_body}
        terminals = []
        for node in body_desc:
            # Inner-loop body terminals must loop to the inner header, not also
            # jump directly to the enclosing loop header.
            if node in nested_body_nodes:
                continue
            kind_n = G.nodes[node].get("node_type", "")
            if kind_n in TERMINATING_KINDS:
                continue
            outgoing_inside = False
            for _, target, data in G.out_edges(node, data=True):
                typ = edge_type(data)
                if target in body_desc and typ.startswith("CFG_") and typ not in REBUILT_LOOP_EDGE_TYPES:
                    outgoing_inside = True
                    break
            # Nested loop exit nodes are not AST descendants; treat them as
            # continuations if a CFG edge enters them from this body's AST.
            if not outgoing_inside:
                terminals.append(node)
        for terminal in terminals:
            add_edge_once(G, terminal, loop, "CFG_LOOP_BACK",
                          semantics="approximate_end_of_iteration")

    # Determine loop nesting from AST ancestry. An AST descendant may belong to
    # multiple loops; store all enclosing loop IDs, nearest first by source nesting
    # proxy (smaller descendant set is the inner loop).
    for node, data in G.nodes(data=True):
        memberships = []
        for loop, info in loop_info.items():
            if node in info["body_nodes"]:
                memberships.append(loop)
        memberships.sort(key=lambda l: len(loop_info[l]["body_nodes"]))
        if memberships:
            data["loop_body_member"] = True
            data["loop_depth"] = len(memberships)
            data["enclosing_loop_headers"] = json.dumps([str(x) for x in memberships])

    # Link concrete input examples to loops when parameter references occur in the
    # loop AST. These links show potential input dependence, not evaluated paths.
    params_by_function = {}
    for node, data in G.nodes(data=True):
        if data.get("node_type") == "PARM_DECL":
            fn = data.get("function", "")
            name = data.get("label", "")
            if fn and name:
                params_by_function.setdefault(fn, {})[name] = node

    for loop, info in loop_info.items():
        fn = G.nodes[loop].get("function", "")
        refs = set()
        for node in info["all_descendants"]:
            if G.nodes[node].get("node_type") == "DECL_REF_EXPR":
                label = G.nodes[node].get("label", "")
                if label:
                    refs.add(label)
        for name in sorted(refs):
            param_node = params_by_function.get(fn, {}).get(name)
            if param_node:
                add_edge_once(G, param_node, loop, "INPUT_CONTROLS",
                              parameter=name,
                              example_value=G.nodes[param_node].get("example_value", ""),
                              semantics="parameter_occurs_in_loop_ast_not_path_evaluation")
                G.nodes[loop]["input_dependent_parameters"] = json.dumps(sorted(
                    set(json.loads(G.nodes[loop].get("input_dependent_parameters", "[]"))) | {name}
                ))

    # Explicitly label the epistemic status of dependency edges.
    for _, _, data in G.edges(data=True):
        if edge_type(data) == "DATA_DEP":
            data["dependency_quality"] = "conservative_name_based_hint"

    # Per-graph structural audit.
    audit = {"source_file": str(source_path), "loop_count": len(loops),
             "loops": [], "data_dependency_edges": 0,
             "input_control_edges": 0, "warnings": []}
    for loop in loops:
        info = loop_info.get(loop)
        if not info:
            audit["warnings"].append(f"No body identified for {loop}")
            continue
        back_edges = [(u, v) for u, v, d in G.edges(data=True)
                      if v == loop and edge_type(d) == "CFG_LOOP_BACK"]
        input_edges = [(u, v) for u, v, d in G.edges(data=True)
                       if v == loop and edge_type(d) == "INPUT_CONTROLS"]
        audit["loops"].append({"header": str(loop), "kind": info["kind"],
                               "body_root": str(info["body"]),
                               "body_ast_node_count": len(info["body_nodes"]),
                               "loop_back_edge_count": len(back_edges),
                               "input_control_parameters": [G.nodes[u].get("label", "") for u, _ in input_edges]})
        if not back_edges:
            audit["warnings"].append(f"Loop {loop} has no CFG_LOOP_BACK edge")
    audit["data_dependency_edges"] = sum(1 for _, _, d in G.edges(data=True)
                                          if edge_type(d) == "DATA_DEP")
    audit["input_control_edges"] = sum(1 for _, _, d in G.edges(data=True)
                                        if edge_type(d) == "INPUT_CONTROLS")
    G.graph["graph_semantics"] = (
        "AST + approximate CFG; refined loop body membership/back/exit edges; "
        "conservative name-based DATA_DEP; INPUT_CONTROLS marks parameter references, "
        "not concrete path execution"
    )
    G.graph["refinement_stage"] = "acsl_graph3_cfg_refine.py"
    G.graph["loop_header_count"] = len(loops)
    G.graph["data_dependency_edge_count"] = audit["data_dependency_edges"]
    G.graph["input_control_edge_count"] = audit["input_control_edges"]
    return G, audit


def main():
    parser = argparse.ArgumentParser(description="Refine and audit AST/CFG graphs in a separate output directory.")
    parser.add_argument("--input-dir", default="acsl_CFiles-Exp5",
                        help="Root directory containing the C source variants")
    parser.add_argument("--graph-dir", default=None,
                        help="Output graph directory (default: INPUT_DIR/graphs_refined)")
    parser.add_argument("--libclang", default=None)
    parser.add_argument("--clang-arg", action="append", default=[],
                        help="Extra Clang argument; repeat as needed, e.g. --clang-arg=-Iinclude")
    args = parser.parse_args()

    configure_clang(args.libclang)
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.graph_dir).resolve() if args.graph_dir else input_dir / "graphs_refined"
    output_dir.mkdir(parents=True, exist_ok=True)
    input_out = output_dir / "inputs"
    input_out.mkdir(parents=True, exist_ok=True)
    report_dir = output_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    summary = {"input_dir": str(input_dir), "output_dir": str(output_dir),
               "files_processed": 0, "files_failed": 0, "loop_count": 0,
               "data_dependency_edges": 0, "input_control_edges": 0, "errors": []}

    for root, dirs, files in os.walk(input_dir):
        dirs[:] = [d for d in dirs if d not in {"graphs", "graphs_refined", "embeddings", "__pycache__", ".venv"}]
        for filename in sorted(files):
            if not filename.endswith(".c"):
                continue
            source = Path(root) / filename
            rel = source.resolve().relative_to(input_dir)
            print(f"Refining: {rel}")
            try:
                G, examples, _tu = build_graph(source, args.clang_arg)
                G, audit = enrich_graph(G, source, examples)
                out = output_dir / (str(rel) + ".graphml")
                out.parent.mkdir(parents=True, exist_ok=True)
                nx.write_graphml(G, out)
                (input_out / (str(rel) + ".json")).parent.mkdir(parents=True, exist_ok=True)
                (input_out / (str(rel) + ".json")).write_text(json.dumps(
                    {"source": str(rel), "functions": examples,
                     "note": "Example inputs are deterministic templates; validate preconditions, pointer lengths, and array bounds before execution."}, indent=2), encoding="utf-8")
                report = report_dir / (str(rel) + ".json")
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text(json.dumps(audit, indent=2), encoding="utf-8")
                summary["files_processed"] += 1
                summary["loop_count"] += audit["loop_count"]
                summary["data_dependency_edges"] += audit["data_dependency_edges"]
                summary["input_control_edges"] += audit["input_control_edges"]
                print(f"  loops={audit['loop_count']} data_dep={audit['data_dependency_edges']} input_controls={audit['input_control_edges']} -> {out}")
                if audit["warnings"]:
                    print("  WARNINGS: " + "; ".join(audit["warnings"]))
            except Exception as exc:
                summary["files_failed"] += 1
                message = f"{rel}: {exc}"
                summary["errors"].append(message)
                print(f"  ERROR: {exc}")

    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nRefinement complete.")
    print(f"Files processed: {summary['files_processed']}; failed: {summary['files_failed']}")
    print(f"Loop headers: {summary['loop_count']}; DATA_DEP edges: {summary['data_dependency_edges']}; INPUT_CONTROLS edges: {summary['input_control_edges']}")
    print(f"Graphs: {output_dir}")
    print(f"Summary report: {report_dir / 'summary.json'}")
    print("This script does not execute C or prove path feasibility; CFG and data dependencies remain approximations.")

if __name__ == "__main__":
    main()
