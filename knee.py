"""An Python re-implementation of hierarchical module import.

This code is intended to be read, not executed.  However, it does work
-- all you need to do to enable it is "import knee".

(The name is a pun on the klunkier predecessor of this module, "ni".)

Source: https://svn.python.org/projects/python/trunk/Demo/imputil/knee.py
"""

import sys, imp, __builtin__


"""
We will override __import__ with import_hook later on.

__import__'s signature is (name[, globals[, locals[, fromlist[, level]]]])
  (From https://docs.python.org/2/library/functions.html#__import__ )

What repyportability will need to do is import a library 
* by filename ("foo.r2py")
* with globals set (so the Repy API calls are defined)
"""

def import_hook(name, globals=None, locals=None, fromlist=None):
    parent = determine_parent(globals) # returns None
    q, tail = find_head_package(parent, name)
    m = load_tail(q, tail)
    if not fromlist:
        return q
    if hasattr(m, "__path__"):
        ensure_fromlist(m, fromlist)
    return m

def determine_parent(globals):
    """I haven't seen this first test return, ever.
* Importing a library, either from a file or on the Python prompt, 
sets __name__ to the module name.
* If the library is run as a program, __name__ is "__main__".

Thus, `pname` below seems to be always populated.
"""
    if not globals or  not globals.has_key("__name__"):
        return None

    pname = globals['__name__']

    """From my tests, neither `if` clause evaluates to True. Skip!"""
    if globals.has_key("__path__"):
        parent = sys.modules[pname]
        assert globals is parent.__dict__
        return parent
    if '.' in pname:
        i = pname.rfind('.')
        pname = pname[:i]
        parent = sys.modules[pname]
        assert parent.__name__ == pname
        return parent
    """So we return None eventually"""
    return None



def find_head_package(parent, name):
    if '.' in name:  # Nope
        i = name.find('.')
        head = name[:i]
        tail = name[i+1:]
    else:  # Yes!
        head = name
        tail = ""
    if parent:  # Nope
        qname = "%s.%s" % (parent.__name__, head)
    else:  # Yes!
        qname = head
    """We have
* head = name,
* tail = "",
* qname = head,
and parent = None (from our caller)"""
    q = import_module(head, qname, parent)
    if q:
        return q, tail

    if parent:
        qname = head
        parent = None
        q = import_module(head, qname, parent)
        if q: return q, tail
    raise ImportError, "No module named " + qname



def load_tail(q, tail):
    m = q
    while tail:
        i = tail.find('.')
        if i < 0: i = len(tail)
        head, tail = tail[:i], tail[i+1:]
        mname = "%s.%s" % (m.__name__, head)
        m = import_module(head, mname, m)
        if not m:
            raise ImportError, "No module named " + mname
    return m



def ensure_fromlist(m, fromlist, recursive=0):
    for sub in fromlist:
        if sub == "*":
            if not recursive:
                try:
                    all = m.__all__
                except AttributeError:
                    pass
                else:
                    ensure_fromlist(m, all, 1)
            continue
        if sub != "*" and not hasattr(m, sub):
            subname = "%s.%s" % (m.__name__, sub)
            submod = import_module(sub, subname, m)
            if not submod:
                raise ImportError, "No module named " + subname



def import_module(partname, fqname, parent):
    """Called with params (partname=name, fqname=name, parent=None),
where `name` is the first parameter to `import_hook`."""
    # Don't `reload` the module if it is in the modules cache already.
    try:
        return sys.modules[fqname]
    except KeyError:
        pass

    """We essentially know where the file is and how it is called, 
so we set the file pointer `fp`, `pathname`, and `stuff` all manually 
without calling `find_module`:

* fp = open("whatever_repyv2_lib_we_want_imported.r2py", "r")
* pathname = os.path.realtpath(that_lib)
* `stuff` is a tuple (suffix, mode, type) as returned by `imp.get_suffixes()`. 
For RepyV2 code, it will be (".r2py", "r", imp.PY_SOURCE)."""
    try:
        fp, pathname, stuff = imp.find_module(partname,
                                              parent and parent.__path__)
    except ImportError:
        return None

    try:
        m = imp.load_module(fqname, fp, pathname, stuff)
    finally:
        if fp: fp.close()
    if parent:
        setattr(parent, partname, m)
    return m



# Replacement for reload()
def reload_hook(module):
    name = module.__name__
    if '.' not in name:
        return import_module(name, name, None)
    i = name.rfind('.')
    pname = name[:i]
    parent = sys.modules[pname]
    return import_module(name[i+1:], name, parent)



# Save the original hooks
original_import = __builtin__.__import__
original_reload = __builtin__.reload

# Now install our hooks
__builtin__.__import__ = import_hook
__builtin__.reload = reload_hook

