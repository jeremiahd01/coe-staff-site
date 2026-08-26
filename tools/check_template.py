#!/usr/bin/env python3
"""Pre-flight checks for a Zope 2.13 page template.

Catches the failure modes that only show up on paste into the ZMI, which a
local render with a modern zope.tales will happily let through:

  * multi-line python: expressions that are not bracketed
        Zope 2.13 compiles the expression as written. An unbracketed
        continuation is an IndentationError ("unexpected indent"). Newer
        zope.tales collapses newlines first, so a local render passes and the
        ZMI still rejects it. The ZMI also stores CRLF, which makes it worse.
  * python: expressions that are not valid Python 2-compatible syntax
  * entity-escaping traps: apostrophes inside single-quoted Python strings
  * XML well-formedness
  * non-ASCII bytes anywhere in the file
        The ZMI stores pasted source as Latin-1. A literal en dash in a Python
        script comes back as mojibake ("Oct 27 a Nov 10"), and the same applies
        to templates and to CSS, which the wrap serves as iso-8859-15. Write
        non-ASCII as an escape: u'\\u2013' in Python, &#8211; in a template,
        \\2013 in CSS.

Usage: python3 tools/check_template.py zope/dashboard_home.pt
"""
import html
import re
import sys
import xml.etree.ElementTree as ET

TAL_ATTR = re.compile(
    r'tal:(?:define|attributes|content|condition|repeat|replace)="([^"]*)"', re.S)


def check(path):
    data = open(path, 'rb').read()
    raw = data.decode('utf-8')
    problems = []

    # Non-ASCII is the highest-value check here: it survives every local test
    # and only misbehaves once the ZMI has stored it.
    try:
        data.decode('ascii')
    except UnicodeDecodeError:
        offenders = {}
        for number, line in enumerate(raw.split('\n'), 1):
            for ch in line:
                if ord(ch) > 127:
                    offenders.setdefault(ch, []).append(number)
        for ch, lines in sorted(offenders.items()):
            problems.append('non-ASCII U+%04X (%d occurrence(s), first line %d) '
                            '- write it as an escape'
                            % (ord(ch), len(lines), lines[0]))

    if path.endswith('.pt'):
        try:
            ET.fromstring(raw.encode('utf-8'))
        except ET.ParseError as exc:
            problems.append('XML not well-formed: %s' % exc)

    expressions = []
    if path.endswith('.pt'):
        for attr in TAL_ATTR.findall(raw):
            decoded = html.unescape(attr)
            for chunk in decoded.split(';'):
                marker = chunk.find('python:')
                if marker > -1:
                    expressions.append(chunk[marker + len('python:'):])

    for expr in expressions:
        label = ' '.join(expr.split())[:64]

        # Zope 2.13 sees the expression as written, CRLF and all.
        as_stored = expr.replace('\n', '\r\n')
        try:
            compile(as_stored, '<expr>', 'eval')
        except SyntaxError as exc:
            problems.append('%s: %s\n      %s' % (
                type(exc).__name__, exc.msg, label))
            continue

        # And it must still be valid once newlines collapse, for engines that do.
        try:
            compile(' '.join(expr.split()), '<expr>', 'eval')
        except SyntaxError as exc:
            problems.append('collapses to invalid Python: %s\n      %s' % (
                exc.msg, label))

    # An apostrophe inside a single-quoted Python string, written as &#39;,
    # is unescaped by the XML parser before TALES sees it and ends the string.
    if "&#39;" in raw:
        problems.append("&#39; present: inside a single-quoted Python string it "
                        "terminates the string. Use &quot; delimiters instead.")

    print('%s: %d python: expression(s) checked' % (path, len(expressions)))
    if problems:
        print('FAILED')
        for problem in problems:
            print('  - %s' % problem)
        return 1
    print('OK')
    return 0


DEFAULTS = ['zope/dashboard_home.pt',
            'zope/scripts/get_staff_dashboard_data.py',
            'prototype/staff-dashboard.css']

if __name__ == '__main__':
    sys.exit(max(check(p) for p in (sys.argv[1:] or DEFAULTS)))
