##parameters=
##title=Discovery: which builtins and modules restricted Python exposes
##
# ============================================================================
# Run once, paste the output back, then delete. Reads only, changes nothing.
#
# Install: ZMI -> /staff -> Add Script (Python), id "introspect_sandbox".
#          Visit https://engineering.purdue.edu/staff/introspect_sandbox
#
# Why: this instance withholds sorted(), which most Zope installs allow, so no
# builtin can be assumed. Every widget bug of the form "NameError at request
# time" traces back to guessing. This reports what is actually available, once,
# so the answer stops being discovered one error at a time.
#
# A name is probed by referencing it inside try/except - an absent name raises
# NameError - and a module by importing it, which the guarded import turns into
# an ImportError when it is not on the allow list.
# ============================================================================

request = context.REQUEST
request.RESPONSE.setHeader('Content-Type', 'text/plain; charset=utf-8')

available = []
missing = []

try:
    abs
    available.append('abs')
except Exception:
    missing.append('abs')

try:
    all
    available.append('all')
except Exception:
    missing.append('all')

try:
    any
    available.append('any')
except Exception:
    missing.append('any')

try:
    bool
    available.append('bool')
except Exception:
    missing.append('bool')

try:
    callable
    available.append('callable')
except Exception:
    missing.append('callable')

try:
    chr
    available.append('chr')
except Exception:
    missing.append('chr')

try:
    cmp
    available.append('cmp')
except Exception:
    missing.append('cmp')

try:
    dict
    available.append('dict')
except Exception:
    missing.append('dict')

try:
    dir
    available.append('dir')
except Exception:
    missing.append('dir')

try:
    divmod
    available.append('divmod')
except Exception:
    missing.append('divmod')

try:
    enumerate
    available.append('enumerate')
except Exception:
    missing.append('enumerate')

try:
    filter
    available.append('filter')
except Exception:
    missing.append('filter')

try:
    float
    available.append('float')
except Exception:
    missing.append('float')

try:
    getattr
    available.append('getattr')
except Exception:
    missing.append('getattr')

try:
    hasattr
    available.append('hasattr')
except Exception:
    missing.append('hasattr')

try:
    hash
    available.append('hash')
except Exception:
    missing.append('hash')

try:
    hex
    available.append('hex')
except Exception:
    missing.append('hex')

try:
    id
    available.append('id')
except Exception:
    missing.append('id')

try:
    int
    available.append('int')
except Exception:
    missing.append('int')

try:
    isinstance
    available.append('isinstance')
except Exception:
    missing.append('isinstance')

try:
    issubclass
    available.append('issubclass')
except Exception:
    missing.append('issubclass')

try:
    len
    available.append('len')
except Exception:
    missing.append('len')

try:
    list
    available.append('list')
except Exception:
    missing.append('list')

try:
    long
    available.append('long')
except Exception:
    missing.append('long')

try:
    map
    available.append('map')
except Exception:
    missing.append('map')

try:
    max
    available.append('max')
except Exception:
    missing.append('max')

try:
    min
    available.append('min')
except Exception:
    missing.append('min')

try:
    oct
    available.append('oct')
except Exception:
    missing.append('oct')

try:
    ord
    available.append('ord')
except Exception:
    missing.append('ord')

try:
    pow
    available.append('pow')
except Exception:
    missing.append('pow')

try:
    range
    available.append('range')
except Exception:
    missing.append('range')

try:
    repr
    available.append('repr')
except Exception:
    missing.append('repr')

try:
    reversed
    available.append('reversed')
except Exception:
    missing.append('reversed')

try:
    round
    available.append('round')
except Exception:
    missing.append('round')

try:
    set
    available.append('set')
except Exception:
    missing.append('set')

try:
    setattr
    available.append('setattr')
except Exception:
    missing.append('setattr')

try:
    sorted
    available.append('sorted')
except Exception:
    missing.append('sorted')

try:
    str
    available.append('str')
except Exception:
    missing.append('str')

try:
    sum
    available.append('sum')
except Exception:
    missing.append('sum')

try:
    tuple
    available.append('tuple')
except Exception:
    missing.append('tuple')

try:
    type
    available.append('type')
except Exception:
    missing.append('type')

try:
    unichr
    available.append('unichr')
except Exception:
    missing.append('unichr')

try:
    unicode
    available.append('unicode')
except Exception:
    missing.append('unicode')

try:
    xrange
    available.append('xrange')
except Exception:
    missing.append('xrange')

try:
    zip
    available.append('zip')
except Exception:
    missing.append('zip')

try:
    basestring
    available.append('basestring')
except Exception:
    missing.append('basestring')

try:
    frozenset
    available.append('frozenset')
except Exception:
    missing.append('frozenset')

try:
    slice
    available.append('slice')
except Exception:
    missing.append('slice')

try:
    vars
    available.append('vars')
except Exception:
    missing.append('vars')

try:
    globals
    available.append('globals')
except Exception:
    missing.append('globals')

try:
    locals
    available.append('locals')
except Exception:
    missing.append('locals')

try:
    apply
    available.append('apply')
except Exception:
    missing.append('apply')

try:
    open
    available.append('open')
except Exception:
    missing.append('open')

try:
    compile
    available.append('compile')
except Exception:
    missing.append('compile')

try:
    eval
    available.append('eval')
except Exception:
    missing.append('eval')

try:
    execfile
    available.append('execfile')
except Exception:
    missing.append('execfile')

try:
    input
    available.append('input')
except Exception:
    missing.append('input')

try:
    raw_input
    available.append('raw_input')
except Exception:
    missing.append('raw_input')



mods_ok = []
mods_no = []

try:
    import json
    mods_ok.append('json')
except Exception:
    mods_no.append('json')

try:
    import re
    mods_ok.append('re')
except Exception:
    mods_no.append('re')

try:
    import string
    mods_ok.append('string')
except Exception:
    mods_no.append('string')

try:
    import math
    mods_ok.append('math')
except Exception:
    mods_no.append('math')

try:
    import random
    mods_ok.append('random')
except Exception:
    mods_no.append('random')

try:
    import datetime
    mods_ok.append('datetime')
except Exception:
    mods_no.append('datetime')

try:
    import time
    mods_ok.append('time')
except Exception:
    mods_no.append('time')

try:
    import base64
    mods_ok.append('base64')
except Exception:
    mods_no.append('base64')

try:
    import urllib
    mods_ok.append('urllib')
except Exception:
    mods_no.append('urllib')

try:
    import urlparse
    mods_ok.append('urlparse')
except Exception:
    mods_no.append('urlparse')

try:
    import cgi
    mods_ok.append('cgi')
except Exception:
    mods_no.append('cgi')

try:
    import hashlib
    mods_ok.append('hashlib')
except Exception:
    mods_no.append('hashlib')

try:
    import itertools
    mods_ok.append('itertools')
except Exception:
    mods_no.append('itertools')

try:
    import collections
    mods_ok.append('collections')
except Exception:
    mods_no.append('collections')

try:
    import operator
    mods_ok.append('operator')
except Exception:
    mods_no.append('operator')

try:
    import functools
    mods_ok.append('functools')
except Exception:
    mods_no.append('functools')

try:
    import copy
    mods_ok.append('copy')
except Exception:
    mods_no.append('copy')

try:
    import decimal
    mods_ok.append('decimal')
except Exception:
    mods_no.append('decimal')

try:
    import uuid
    mods_ok.append('uuid')
except Exception:
    mods_no.append('uuid')

try:
    import csv
    mods_ok.append('csv')
except Exception:
    mods_no.append('csv')

try:
    import textwrap
    mods_ok.append('textwrap')
except Exception:
    mods_no.append('textwrap')

try:
    from DateTime import DateTime
    mods_ok.append('from DateTime import DateTime')
except Exception:
    mods_no.append('from DateTime import DateTime')

try:
    from Products.PythonScripts.standard import html_quote
    mods_ok.append('from Products.PythonScripts.standard import html_quote')
except Exception:
    mods_no.append('from Products.PythonScripts.standard import html_quote')

try:
    from ZTUtils import make_query
    mods_ok.append('from ZTUtils import make_query')
except Exception:
    mods_no.append('from ZTUtils import make_query')

try:
    from AccessControl import getSecurityManager
    mods_ok.append('from AccessControl import getSecurityManager')
except Exception:
    mods_no.append('from AccessControl import getSecurityManager')

try:
    from Products.CMFCore.utils import getToolByName
    mods_ok.append('from Products.CMFCore.utils import getToolByName')
except Exception:
    mods_no.append('from Products.CMFCore.utils import getToolByName')


out = []
out.append('Restricted Python sandbox report')
out.append('')
out.append('BUILTINS AVAILABLE (%s)' % len(available))
out.append('  ' + ', '.join(available))
out.append('')
out.append('BUILTINS NOT AVAILABLE (%s)   <-- never use these' % len(missing))
out.append('  ' + (', '.join(missing) or 'none'))
out.append('')
out.append('MODULES IMPORTABLE (%s)' % len(mods_ok))
out.append('  ' + (', '.join(mods_ok) or 'none'))
out.append('')
out.append('MODULES NOT IMPORTABLE (%s)' % len(mods_no))
out.append('  ' + (', '.join(mods_no) or 'none'))
out.append('')
out.append('The json line is the one that decides how dashboard link lists get')
out.append('stored: no json module means no JSON file as a data source.')
out.append('')
out.append('End of report.')

return '\n'.join(out)
