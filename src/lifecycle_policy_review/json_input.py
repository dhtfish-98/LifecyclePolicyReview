"""Bounded strict JSON bytes; duplicate keys and coercion are never policies."""

import json

from .model import InputIssue


def decode(raw, limits):
    if type(raw) is not bytes:
        raise InputIssue("input_immutable_bytes_required")
    if not raw or len(raw) > limits.file_bytes:
        raise InputIssue("input_byte_budget")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputIssue("json_utf8_invalid") from None
    # Before the recursive stdlib decoder, bound actual container nesting outside
    # strings. This is a budget pre-scan; the decoder still validates all syntax.
    stack, string, escaped, tokens = [], False, False, 0
    for char in text:
        if string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                string = False
        elif char == '"':
            string = True
            tokens += 1
        elif char in "[{":
            stack.append(char)
            tokens += 1
            if len(stack) > limits.depth:
                raise InputIssue("json_depth_budget")
        elif char in "]}" and stack:
            stack.pop()
        if tokens > limits.nodes:
            raise InputIssue("json_node_budget")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise InputIssue("json_duplicate_key")
            value[key] = item
        return value

    def integer(value):
        if len(value.lstrip("-")) > 128:
            raise InputIssue("json_integer_budget")
        return int(value)

    def nonfinite(_):
        raise InputIssue("json_number_invalid")

    try:
        result = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_int=integer,
            parse_constant=nonfinite,
            parse_float=nonfinite,
        )
    except (UnicodeError, ValueError, RecursionError):
        raise InputIssue("json_syntax_invalid") from None
    # Iterative full walk covers ignored package metadata too: no unpaired
    # surrogates, floats or enormous string fields hiding in unused branches.
    pending, count = [result], 0
    while pending:
        value = pending.pop()
        count += 1
        if count > limits.nodes:
            raise InputIssue("json_node_budget")
        if type(value) is str:
            try:
                if len(value.encode("utf-8", "strict")) > limits.string_bytes:
                    raise InputIssue("json_string_budget")
            except UnicodeError:
                raise InputIssue("json_surrogate_invalid") from None
        elif type(value) is dict:
            pending.extend(value.keys())
            pending.extend(value.values())
        elif type(value) is list:
            pending.extend(value)
    return result
