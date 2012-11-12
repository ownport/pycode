#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
pycode.py

Simple script for python code analysis

Based on standard module: pydoc
'''

import os
import re
import sys
import pydoc
import pprint
import inspect

from traceback import extract_tb

try:
    import builtins as _builtins
except:
    import __builtin__ as _builtins

class _OldStyleClass: pass
_OLD_INSTANCE_TYPE = type(_OldStyleClass())

def ispath(x):
    return isinstance(x, str) and x.find(os.sep) >= 0

def describe(thing):
    """Produce a short description of the given thing.
    Returns (thing_name, description)"""
    if inspect.ismodule(thing):
        if thing.__name__ in sys.builtin_module_names:
            return (thing.__name__, 'built-in module')
        if hasattr(thing, '__path__'):
            return (thing.__name__, 'package')
        else:
            return (thing.__name__, 'module')
    if inspect.isbuiltin(thing):
        return (thing.__name__, 'built-in function')
    if inspect.isgetsetdescriptor(thing):
        return (thing.__name__,
                'getset descriptor %s.%s.%s' % (thing.__objclass__.__module__, 
                                                thing.__objclass__.__name__))
    if inspect.ismemberdescriptor(thing):
        return (thing.__name__,
                'member descriptor %s.%s.%s' % (thing.__objclass__.__module__, 
                                                thing.__objclass__.__name__))
    if inspect.isclass(thing):
        return (thing.__name__, 'class') 
    if inspect.isfunction(thing):
        return (thing.__name__, 'function')
    if inspect.ismethod(thing):
        return (thing.__name__, 'method')
    if type(thing) is types.InstanceType:
        return (thing.__name__, 'instance of ' + thing.__class__.__name__)
    return (thing.__name__, type(thing).__name__)

def safeimport(path, forceload=0, cache={}):
    """Import a module; handle errors; return None if the module isn't found.

    If the module *is* found but an exception occurs, it's wrapped in an
    ErrorDuringImport exception and reraised.  Unlike __import__, if a
    package path is specified, the module at the end of the path is returned,
    not the package at the beginning.  If the optional 'forceload' argument
    is 1, we reload the module from disk (unless it's a dynamic extension)."""
    try:
        # If forceload is 1 and the module has been previously loaded from
        # disk, we always have to reload the module.  Checking the file's
        # mtime isn't good enough (e.g. the module could contain a class
        # that inherits from another module that has changed).
        if forceload and path in sys.modules:
            if path not in sys.builtin_module_names:
                # Avoid simply calling reload() because it leaves names in
                # the currently loaded module lying around if they're not
                # defined in the new source file.  Instead, remove the
                # module from sys.modules and re-import.  Also remove any
                # submodules because they won't appear in the newly loaded
                # module's namespace if they're already in sys.modules.
                subs = [m for m in sys.modules if m.startswith(path + '.')]
                for key in [path] + subs:
                    # Prevent garbage collection.
                    cache[key] = sys.modules[key]
                    del sys.modules[key]
        module = __import__(path)
    except:
        # Did the error occur before or after the module was found?
        (exc, value, tb) = info = sys.exc_info()
        if path in sys.modules:
            # An error occurred while executing the imported module.
            raise ErrorDuringImport(sys.modules[path].__file__, info)
        elif exc is SyntaxError:
            # A SyntaxError occurred before we could execute the module.
            raise ErrorDuringImport(value.filename, info)
        elif exc is ImportError and extract_tb(tb)[-1][2]=='safeimport':
            # The import error occurred directly in this function,
            # which means there is no such module in the path.
            return None
        else:
            # Some other error occurred during the importing process.
            raise ErrorDuringImport(path, sys.exc_info())
    for part in path.split('.')[1:]:
        try: module = getattr(module, part)
        except AttributeError: return None
    return module

def locate(path):
    """Locate an object by name or dotted path, importing as necessary."""
    parts = [part for part in path.split('.') if part]
    module, n = None, 0
    while n < len(parts):
        nextmodule = safeimport('.'.join(parts[:n+1]))
        if nextmodule: module, n = nextmodule, n + 1
        else: break
    if module:
        obj = module
    else:
        obj = _builtins
    for part in parts[n:]:
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None
    return obj

def resolve(thing):
    """Given an object or a path to an object, get the object and its name."""
    if isinstance(thing, str):
        obj = locate(thing)
        if not obj:
            raise ImportError, 'no Python code found for %r' % thing
        return obj, thing
    else:
        name = getattr(thing, '__name__', None)
        return thing, name if isinstance(name, str) else None

def render_code(code):
    """Render python code, given an object or a path to an object."""
    result = dict()
    obj, name = resolve(code)
    result['name'] = name
    desc, obj_type = describe(obj)
    result['object_type'] = obj_type
    module = inspect.getmodule(obj)
    result['module'] = module
    if type(obj) is _OLD_INSTANCE_TYPE:
        # If the passed object is an instance of an old-style class,
        # document its available methods instead of its value.
        obj = obj.__class__
    elif not (inspect.ismodule(obj) or
              inspect.isclass(obj) or
              inspect.isroutine(obj) or
              inspect.isgetsetdescriptor(obj) or
              inspect.ismemberdescriptor(obj) or
              isinstance(obj, property)):
        # If the passed object is a piece of data or an instance,
        # document its available methods instead of its value.
        obj = type(obj)
        desc += ' object'
    result['object'] = obj
    result['description'] = desc
    code_struct = PyCodeStruct()
    result['struct'] = code_struct.struct(obj, name)
    return result

class PyCodeStruct(object):
    """Formatter class for text documentation."""

    def struct(self, obj, name=None, *args):
    
        """Generate structure for an object."""
        
        args = (obj, name) + args
        if inspect.isgetsetdescriptor(obj): return self.data_struct(*args)
        if inspect.ismemberdescriptor(obj): return self.data_struct(*args)
        if inspect.ismodule(obj): return self.module_struct(*args)
        if inspect.isclass(obj): return self.class_struct(*args)
        if inspect.isroutine(obj): return self.routine_struct(*args)
        if isinstance(obj, property): return self.property_struct(*args)
        return self.other_struct(*args)

    def fail(self, object, name=None, *args):
        """Raise an exception for unimplemented types."""
        message = "don't know how to document object%s of type %s" % (
            name and ' ' + repr(name), type(object).__name__)
        raise TypeError, message

    def getdocloc(self, object):
        """Return the location of module docs or None"""

        try:
            file = inspect.getabsfile(object)
        except TypeError:
            file = '(built-in)'

        docloc = os.environ.get("PYTHONDOCS",
                                "http://docs.python.org/library")
        basedir = os.path.join(sys.exec_prefix, "lib",
                               "python"+sys.version[0:3])
        if (isinstance(object, type(os)) and
            (object.__name__ in ('errno', 'exceptions', 'gc', 'imp',
                                 'marshal', 'posix', 'signal', 'sys',
                                 'thread', 'zipimport') or
             (file.startswith(basedir) and
              not file.startswith(os.path.join(basedir, 'dist-packages')) and
              not file.startswith(os.path.join(basedir, 'site-packages')))) and
            object.__name__ not in ('xml.etree', 'test.pydoc_mod')):
            if docloc.startswith("http://"):
                docloc = "%s/%s" % (docloc.rstrip("/"), object.__name__)
            else:
                docloc = os.path.join(docloc, object.__name__ + ".html")
        else:
            docloc = None
        return docloc

    def bold(self, text):
        """Format a string in bold by overstriking."""
        return join(map(lambda ch: ch + '\b' + ch, text), '')

    def indent(self, text, prefix='    '):
        """Indent text by prepending a given prefix to each line."""
        if not text: return ''
        lines = split(text, '\n')
        lines = map(lambda line, prefix=prefix: prefix + line, lines)
        if lines: lines[-1] = rstrip(lines[-1])
        return join(lines, '\n')

    def section(self, title, contents):
        """Format a section with a given heading."""
        return self.bold(title) + '\n' + rstrip(self.indent(contents)) + '\n\n'

    # ---------------------------------------------- type-specific routines

    def formattree(self, tree, modname, parent=None):
        """Render in text a class tree as returned by inspect.getclasstree()."""
        struct = list()
        for entry in tree:
            if type(entry) is type(()):
                c, bases = entry
                struct.append(pydoc.classname(c, modname))
                if bases and bases != (parent,):
                    parents = map(lambda c, m=modname: pydoc.classname(c, m), bases)
                    #result = result + '(%s)' % join(parents, ', ')
                #result = result + '\n'
            elif type(entry) is type([]):
                struct.append(self.formattree(entry, modname, c))
        return struct

    def module_struct(self, object, name=None, mod=None):
        """Produce structure for a given module object."""
        
        struct = dict()
        name = object.__name__ # ignore the passed-in name
        struct['synop'], struct['description'] = pydoc.splitdoc(pydoc.getdoc(object))

        try:
            all = object.__all__
        except AttributeError:
            all = None

        try:
            struct['file'] = inspect.getabsfile(object)
        except TypeError:
            struct['file'] = '(built-in)'

        docloc = self.getdocloc(object)
        if docloc is not None:
            struct['module_docs'] = docloc

        classes = []
        for key, value in inspect.getmembers(object, inspect.isclass):
            # if __all__ exists, believe it.  Otherwise use old heuristic.
            if (all is not None
                or (inspect.getmodule(value) or object) is object):
                if pydoc.visiblename(key, all, object):
                    classes.append((key, value))
        funcs = []
        for key, value in inspect.getmembers(object, inspect.isroutine):
            # if __all__ exists, believe it.  Otherwise use old heuristic.
            if (all is not None or
                inspect.isbuiltin(value) or inspect.getmodule(value) is object):
                if pydoc.visiblename(key, all, object):
                    funcs.append((key, value))
        data = []
        for key, value in inspect.getmembers(object, pydoc.isdata):
            if pydoc.visiblename(key, all, object):
                data.append((key, value))

        modpkgs = []
        modpkgs_names = set()
        if hasattr(object, '__path__'):
            for importer, modname, ispkg in pkgutil.iter_modules(object.__path__):
                modpkgs_names.add(modname)
                if ispkg:
                    modpkgs.append(modname + ' (package)')
                else:
                    modpkgs.append(modname)

            modpkgs.sort()
            struct['package_contents'] = '\n'.join(modpkgs)

        # Detect submodules as sometimes created by C extensions
        submodules = []
        for key, value in inspect.getmembers(object, inspect.ismodule):
            if value.__name__.startswith(name + '.') and key not in modpkgs_names:
                submodules.append(key)
        if submodules:
            submodules.sort()
            result = result + self.section(
                'SUBMODULES', join(submodules, '\n'))

        if classes:
            classlist = map(lambda key_value: key_value[1], classes)
            contents = [self.formattree(
                inspect.getclasstree(classlist, 1), name)]
            for key, value in classes:
                contents.append(self.document(value, key, name))
            result = result + self.section('CLASSES', join(contents, '\n'))

        if funcs:
            contents = []
            for key, value in funcs:
                contents.append(self.document(value, key, name))
            result = result + self.section('FUNCTIONS', join(contents, '\n'))

        if data:
            contents = []
            for key, value in data:
                contents.append(self.docother(value, key, name, maxlen=70))
            result = result + self.section('DATA', join(contents, '\n'))

        if hasattr(object, '__version__'):
            version = str(object.__version__)
            if version[:11] == '$' + 'Revision: ' and version[-1:] == '$':
                version = strip(version[11:-1])
            result = result + self.section('VERSION', version)
        if hasattr(object, '__date__'):
            result = result + self.section('DATE', str(object.__date__))
        if hasattr(object, '__author__'):
            result = result + self.section('AUTHOR', str(object.__author__))
        if hasattr(object, '__credits__'):
            result = result + self.section('CREDITS', str(object.__credits__))
        return struct

    def docclass(self, object, name=None, mod=None, *ignored):
        """Produce text documentation for a given class object."""
        realname = object.__name__
        name = name or realname
        bases = object.__bases__

        def makename(c, m=object.__module__):
            return classname(c, m)

        if name == realname:
            title = 'class ' + self.bold(realname)
        else:
            title = self.bold(name) + ' = class ' + realname
        if bases:
            parents = map(makename, bases)
            title = title + '(%s)' % join(parents, ', ')

        doc = getdoc(object)
        contents = doc and [doc + '\n'] or []
        push = contents.append

        # List the mro, if non-trivial.
        mro = deque(inspect.getmro(object))
        if len(mro) > 2:
            push("Method resolution order:")
            for base in mro:
                push('    ' + makename(base))
            push('')

        # Cute little class to pump out a horizontal rule between sections.
        class HorizontalRule:
            def __init__(self):
                self.needone = 0
            def maybe(self):
                if self.needone:
                    push('-' * 70)
                self.needone = 1
        hr = HorizontalRule()

        def spill(msg, attrs, predicate):
            ok, attrs = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for name, kind, homecls, value in ok:
                    try:
                        value = getattr(object, name)
                    except Exception:
                        # Some descriptors may meet a failure in their __get__.
                        # (bug #1785)
                        push(self._docdescriptor(name, value, mod))
                    else:
                        push(self.document(value,
                                        name, mod, object))
            return attrs

        def spilldescriptors(msg, attrs, predicate):
            ok, attrs = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for name, kind, homecls, value in ok:
                    push(self._docdescriptor(name, value, mod))
            return attrs

        def spilldata(msg, attrs, predicate):
            ok, attrs = _split_list(attrs, predicate)
            if ok:
                hr.maybe()
                push(msg)
                for name, kind, homecls, value in ok:
                    if (hasattr(value, '__call__') or
                            inspect.isdatadescriptor(value)):
                        doc = getdoc(value)
                    else:
                        doc = None
                    push(self.docother(getattr(object, name),
                                       name, mod, maxlen=70, doc=doc) + '\n')
            return attrs

        attrs = filter(lambda data: visiblename(data[0], obj=object),
                       classify_class_attrs(object))
        while attrs:
            if mro:
                thisclass = mro.popleft()
            else:
                thisclass = attrs[0][2]
            attrs, inherited = _split_list(attrs, lambda t: t[2] is thisclass)

            if thisclass is __builtin__.object:
                attrs = inherited
                continue
            elif thisclass is object:
                tag = "defined here"
            else:
                tag = "inherited from %s" % classname(thisclass,
                                                      object.__module__)

            # Sort attrs by name.
            attrs.sort()

            # Pump out the attrs, segregated by kind.
            attrs = spill("Methods %s:\n" % tag, attrs,
                          lambda t: t[1] == 'method')
            attrs = spill("Class methods %s:\n" % tag, attrs,
                          lambda t: t[1] == 'class method')
            attrs = spill("Static methods %s:\n" % tag, attrs,
                          lambda t: t[1] == 'static method')
            attrs = spilldescriptors("Data descriptors %s:\n" % tag, attrs,
                                     lambda t: t[1] == 'data descriptor')
            attrs = spilldata("Data and other attributes %s:\n" % tag, attrs,
                              lambda t: t[1] == 'data')
            assert attrs == []
            attrs = inherited

        contents = '\n'.join(contents)
        if not contents:
            return title + '\n'
        return title + '\n' + self.indent(rstrip(contents), ' |  ') + '\n'

    def formatvalue(self, object):
        """Format an argument default value as text."""
        return '=' + self.repr(object)

    def docroutine(self, object, name=None, mod=None, cl=None):
        """Produce text documentation for a function or method object."""
        realname = object.__name__
        name = name or realname
        note = ''
        skipdocs = 0
        if inspect.ismethod(object):
            imclass = object.im_class
            if cl:
                if imclass is not cl:
                    note = ' from ' + classname(imclass, mod)
            else:
                if object.im_self is not None:
                    note = ' method of %s instance' % classname(
                        object.im_self.__class__, mod)
                else:
                    note = ' unbound %s method' % classname(imclass,mod)
            object = object.im_func

        if name == realname:
            title = self.bold(realname)
        else:
            if (cl and realname in cl.__dict__ and
                cl.__dict__[realname] is object):
                skipdocs = 1
            title = self.bold(name) + ' = ' + realname
        if inspect.isfunction(object):
            args, varargs, varkw, defaults = inspect.getargspec(object)
            argspec = inspect.formatargspec(
                args, varargs, varkw, defaults, formatvalue=self.formatvalue)
            if realname == '<lambda>':
                title = self.bold(name) + ' lambda '
                argspec = argspec[1:-1] # remove parentheses
        else:
            argspec = '(...)'
        decl = title + argspec + note

        if skipdocs:
            return decl + '\n'
        else:
            doc = getdoc(object) or ''
            return decl + '\n' + (doc and rstrip(self.indent(doc)) + '\n')

    def _docdescriptor(self, name, value, mod):
        results = []
        push = results.append

        if name:
            push(self.bold(name))
            push('\n')
        doc = getdoc(value) or ''
        if doc:
            push(self.indent(doc))
            push('\n')
        return ''.join(results)

    def docproperty(self, object, name=None, mod=None, cl=None):
        """Produce text documentation for a property."""
        return self._docdescriptor(name, object, mod)

    def docdata(self, object, name=None, mod=None, cl=None):
        """Produce text documentation for a data descriptor."""
        return self._docdescriptor(name, object, mod)

    def other_struct(self, obj, name=None, mod=None, parent=None, maxlen=None, doc=None):
        """Produce structure for a data object."""
        return {name: str(obj)}

    
def cli():
    """Command-line interface (looks at sys.argv to decide what to do)."""

    import os
    import sys
    import getopt
    class BadUsage: pass

    # Scripts don't get the current directory in their path by default
    # unless they are run with the '-m' switch
    if '' not in sys.path:
        scriptdir = os.path.dirname(sys.argv[0])
        if scriptdir in sys.path:
            sys.path.remove(scriptdir)
        sys.path.insert(0, '.')
    
    try:
        if len(sys.argv) < 2:
            raise BadUsage
        for arg in sys.argv[1:]:
            if ispath(arg) and not os.path.exists(arg):
                print 'file %r does not exist' % arg
                break
            try:
                pprint.pprint(render_code(arg))
            except ImportError, err:
                print err
    except BadUsage:
        cmd = os.path.basename(sys.argv[0])
        print """pycode.py - python code analysis

%s <name> ...
    <name> may be the name of a Python function, module, or package, 
    or a dotted reference to a class or function within a module or 
    module in a package.""" % cmd

if __name__ == '__main__':
    cli()    		
