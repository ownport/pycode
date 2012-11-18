#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
pycode.py

Simple script for python code analysis

Based on module pydoc from standard python library
'''

__author__ = 'Andrey Usov <https://github.com/ownport/pycode>'
__version__ = '0.2'

import os
import re
import sys
import json
import types
import pprint
import inspect

from traceback import extract_tb

try:
    import builtins as _builtins
except:
    import __builtin__ as _builtins

# ------------------------------------------------
# Exceptions
# ------------------------------------------------

class ErrorDuringImport(Exception):
    """Errors that occurred while trying to import something to document it."""
    def __init__(self, filename, exc_info):
        exc, value, tb = exc_info
        self.filename = filename
        self.exc = exc
        self.value = value
        self.tb = tb

    def __str__(self):
        exc = self.exc
        if type(exc) is types.ClassType:
            exc = exc.__name__
        return 'problem in %s - %s: %s' % (self.filename, exc, self.value)

# ------------------------------------------------
# Classes
# ------------------------------------------------
class _OldStyleClass: pass
_OLD_INSTANCE_TYPE = type(_OldStyleClass())


class PyCodeStruct(object):
    ''' extract code structure '''

    def _struct_descriptor(self, name, value, mod):
    
        result = dict()
        result['type'], realname = describe(value)
        result['name'] = name or realname
        result['doc'] = getdoc(value) or ''
        return result

    def struct(self, obj, name=None, *args):
    
        """Generate structure for an object."""
        
        args = (obj, name) + args
        if inspect.isgetsetdescriptor(obj): return self.struct_data(*args)
        if inspect.ismemberdescriptor(obj): return self.struct_data(*args)
        if inspect.ismodule(obj): return self.struct_module(*args)
        if inspect.isclass(obj): return self.struct_class(*args)
        if inspect.isroutine(obj): return self.struct_routine(*args)
        if isinstance(obj, property): return self.struct_property(*args)
        return self.struct_date(*args)

    def struct_data(self, obj, name=None, mod=None, cl=None):
        """Produce structure for a data descriptor."""
        if isinstance(obj, (bool, str, unicode, int, long, float, complex, tuple, list, dict)):
            return dict([(name, obj),])
        result = self._struct_descriptor(name, obj, mod)
        if result and isinstance(result, dict):
            cls_name = classname(cl, mod)
            if cls_name:
                result['belongs_to'] = cls_name
        return result

    def struct_class(self, obj, name=None, mod=None, *ignored):
        """Produce structure for a given class object."""
        
        def spill(attrs):
            # Data descriptors
            # Other
            result = None
            name, kind, homecls, value = attr
            if kind in ('method', 'class method', 'static method'):
                result = self.struct(value, name, mod, homecls)
            elif kind in ('data'):
                result = self.struct_data(value, name, mod, homecls)
            if not result:
                raise RuntimeError('Unknown attribute: {}'.format(attr))
            if isinstance(result, dict):
                result['belongs_to'] = classname(homecls, mod)
            return result
        
        result = dict()
        result['type'], realname = describe(obj)
        result['name'] = name or realname

        if name and name <> realname:
            result['decl'] = name + ' = class ' + realname
 
        result['doc'] = getdoc(obj)

        # List the mro, if non-trivial.
        mro = inspect.getmro(obj)
        if len(mro) > 1:
            result['bases'] = map(lambda c, m=obj.__module__: classname(c,m), mro[1:])

        attrs = filter(lambda data: visiblename(data[0], obj=obj),
                       inspect.classify_class_attrs(obj))
        
        obj_attrs = filter(lambda data: data[2] is obj, attrs)
        inherited_attrs = set(attrs) - set(obj_attrs)
        result['class_attrs'] = [spill(attr) for attr in obj_attrs]
        result['inherited attrs'] = [spill(attr) for attr in inherited_attrs]
        return result

    def struct_routine(self, obj, name=None, mod=None, cl=None):
        """Produce code structure for a function or method object."""
        
        result = dict()
        result['type'], realname = describe(obj)
        result['name'] = name or realname

        if inspect.ismethod(obj):
            imclass = obj.im_class
            if cl:
                if imclass is not cl:
                    result['note'] = 'from ' + classname(imclass, mod)
            else:
                if obj.im_self is not None:
                    result['note'] = 'method of %s instance' % classname(
                        obj.im_self.__class__, mod)
                else:
                    result['note'] = 'unbound %s method' % classname(imclass,mod)
            obj = obj.im_func

        if inspect.isfunction(obj):
            args, varargs, varkw, defaults = inspect.getargspec(obj)
            argspec = inspect.formatargspec(args, varargs, varkw, defaults)
            if result['name'] == '<lambda>':
                argspec = argspec[1:-1] # remove parentheses
        else:
            argspec = '(...)'
        result['decl'] = result['name'] + argspec
        result['doc'] = getdoc(obj) or ''
        return result

    def struct_module(self, obj, name=None, mod=None):
        """Produce structure for a given module object."""
        
        result = dict()

        # if __all__ exists, believe it.  Otherwise use old heuristic.
        try:
            _all = obj.__all__
        except AttributeError:
            _all = None

        docloc = getdocloc(obj)
        if docloc:
            result['doc_location'] = docloc

        # classes
        classes = list()
        for key, value in inspect.getmembers(obj, inspect.isclass):
            if visiblename(key, _all, obj):
                classes.append(self.struct_class(value, key))
        if classes:
            result['classes'] = classes

        # functions
        funcs = list()
        for key, value in inspect.getmembers(obj, inspect.isroutine):
            if visiblename(key, _all, obj):
                funcs.append(self.struct_routine(value, key) )
        if funcs:
            result['funcs'] = funcs
        # data
        data = list()
        for key, value in inspect.getmembers(obj, isdata):
            if visiblename(key, _all, obj) and value is not None:
                data.append(self.struct_data(value, key, mod))
        if data:
            result['data'] = data
        return result

        # modules and packages
        modules = list()
        packages = list()
        modpkgs_names = set()
        if hasattr(obj, '__path__'):
            for importer, modname, ispkg in pkgutil.iter_modules(obj.__path__):
                modpkgs_names.add(modname)
                if ispkg:
                    packages.append(modname)
                else:
                    modules.append(modname)
            if packages:
                result['packages'] = packages
            if modules:
                result['modules'] = modules

        # Detect submodules as sometimes created by C extensions
        submodules = []
        for key, value in inspect.getmembers(object, inspect.ismodule):
            if value.__name__.startswith(name + '.') and key not in modpkgs_names:
                submodules.append(key)
        if submodules:
            result['submodules'] = submodules
        return result



# ------------------------------------------------
# Utils
# ------------------------------------------------

def dict2flat(root_name, source, removeEmptyFields=False):
    ''' returns a simplified "flat" form of the complex hierarchical dictionary '''
    
    def is_simple_elements(source):
        ''' check if the source contains simple element types,
        not lists, tuples, dicts
        '''
        for i in source:
            if isinstance(i, (list, tuple, dict)):
                return False
        return True
    
    flat_dict = {}
    if isinstance(source, (list, tuple)):
        if not is_simple_elements(source):
            for i,e in enumerate(source):
                new_root_name = "%s[%d]" % (root_name,i)
                for k,v in dict2flat(new_root_name,e).items():
                    flat_dict[k] = v
        else:
            flat_dict[root_name] = source
    elif isinstance(source, dict):
        for k,v in source.items():
            if root_name:
                new_root_name = "%s.%s" % (root_name, k)
            else:
                new_root_name = "%s" % k
            for kk, vv in dict2flat(new_root_name,v).items():
                flat_dict[kk] = vv
    else:
        if source is not None:
            flat_dict[root_name] = source
    return flat_dict

def importfile(path):
    """Import a Python source file or compiled file given its path."""
    import imp
    
    magic = imp.get_magic()
    file = open(path, 'r')
    if file.read(len(magic)) == magic:
        kind = imp.PY_COMPILED
    else:
        kind = imp.PY_SOURCE
    file.close()
    filename = os.path.basename(path)
    name, ext = os.path.splitext(filename)
    file = open(path, 'r')
    try:
        module = imp.load_module(name, file, path, (ext, 'r', kind))
    except:
        raise ErrorDuringImport(path, sys.exc_info())
    file.close()
    return module

def safeimport(path):
    """Import a module; handle errors; return None if the module isn't found.

    If the module *is* found but an exception occurs, it's wrapped in an
    ErrorDuringImport exception and reraised.  Unlike __import__, if a
    package path is specified, the module at the end of the path is returned,
    not the package at the beginning."""
    try:
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
            raise ImportError, 'Cannot detect code structure for %r' % thing
        return obj, thing
    else:
        name = getattr(thing, '__name__', None)
        return thing, name if isinstance(name, str) else None

def describe(thing):
    """Produce a short description of the given thing.
    returns thing's type and name """
    
    # inspect.isgeneratorfunction(object)
    # inspect.isgenerator(object)
    # inspect.istraceback(object)
    # inspect.isframe(object)
    # inspect.iscode(object)
    # inspect.isroutine(object)
    # inspect.isabstract(object)
    # inspect.ismethoddescriptor(object)
    # inspect.isdatadescriptor(object)
    
    if inspect.ismodule(thing):
        if thing.__name__ in sys.builtin_module_names:
            return ('built-in module', thing.__name__)
        if hasattr(thing, '__path__'):
            return ('package', thing.__name__)
        else:
            return ('module', thing.__name__)
    if inspect.isbuiltin(thing):
        return ('built-in function', thing.__name__)
    if inspect.isgetsetdescriptor(thing):
        return (
            'getset descriptor', 
            '%s.%s.%s' % (  thing.__objclass__.__module__, 
                            thing.__objclass__.__name__,
                            thing.__name__))
    if inspect.ismemberdescriptor(thing):
        return (
            'member descriptor', 
            '%s.%s.%s' % (  thing.__objclass__.__module__, 
                            thing.__objclass__.__name__,
                            thing.__name__))
    if inspect.isclass(thing):
        return ('class', thing.__name__)
    if inspect.isfunction(thing):
        return ('function', thing.__name__)
    if inspect.ismethod(thing):
        return ('method', thing.__name__)
    if type(thing) is types.InstanceType:
        return ('instance of', thing.__class__.__name__)
    return (type(thing).__name__, '')

def isdata(object):
    """Check if an object is of a type that probably means it's data."""
    return not (inspect.ismodule(object) or inspect.isclass(object) or
                inspect.isroutine(object) or inspect.isframe(object) or
                inspect.istraceback(object) or inspect.iscode(object))

def classname(obj, modname):
    """Get a class name and qualify it with a module name if necessary."""
    try:
        name = obj.__name__
    except AttributeError, err:
        return None
    if obj.__module__ != modname:
        name = obj.__module__ + '.' + name
    return name

def getdoc(obj):
    """Get the doc string or comments for an object."""
    result = inspect.getdoc(obj) or inspect.getcomments(obj)
    return result and re.sub('^ *\n', '', result.rstrip()) or ''

def getdocloc(obj):
    """Return the location of module docs or None"""

    try:
        file = inspect.getabsfile(obj)
    except TypeError:
        file = '(built-in)'

    docloc = os.environ.get("PYTHONDOCS",
                            "http://docs.python.org/library")
    basedir = os.path.join(sys.exec_prefix, "lib",
                           "python"+sys.version[0:3])
    if (isinstance(obj, type(os)) and
        (obj.__name__ in ('errno', 'exceptions', 'gc', 'imp',
                             'marshal', 'posix', 'signal', 'sys',
                             'thread', 'zipimport') or
         (file.startswith(basedir) and
          not file.startswith(os.path.join(basedir, 'dist-packages')) and
          not file.startswith(os.path.join(basedir, 'site-packages')))) and
        object.__name__ not in ('xml.etree', 'test.pydoc_mod')):
        if docloc.startswith("http://"):
            docloc = "%s/%s" % (docloc.rstrip("/"), obj.__name__)
        else:
            docloc = os.path.join(docloc, obj.__name__ + ".html")
    else:
        docloc = None
    return docloc


def visiblename(name, all=None, obj=None):
    """Decide whether to show variable."""
    # Certain special names are redundant.
    _hidden_names = ('__builtins__', '__doc__', '__file__', '__path__',
                     '__module__', '__name__', '__slots__', '__package__')
    if name in _hidden_names: return 0
    # Private names are hidden, but special names are displayed.
    if name.startswith('__') and name.endswith('__'): return 1
    # Namedtuples have public fields and methods with a single leading underscore
    if name.startswith('_') and hasattr(obj, '_fields'):
        return 1
    if all is not None:
        # only exported in __all__
        return name in all
    else:
        return not name.startswith('_')

def struct_code(thing):
    """ returns code structure, given an object or a path to an object."""
    result = dict()
    obj, result['name'] = resolve(thing)    
    result['type'], name = describe(obj)
    module = inspect.getmodule(obj)
    result['module_name'] = module.__name__
    result['module_doc'] = module.__doc__

    try:
        result['file'] = inspect.getabsfile(obj)
    except TypeError:
        result['file'] = '(built-in)'
    
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
    code_struct = PyCodeStruct()
    result['struct'] = code_struct.struct(obj, result['name'])
    return result
        
def cli():
    """Command-line interface (looks at sys.argv to decide what to do)."""

    import getopt

    def ispath(x):
        return isinstance(x, str) and x.find(os.sep) >= 0

    # Scripts don't get the current directory in their path by default
    # unless they are run with the '-m' switch
    if '' not in sys.path:
        scriptdir = os.path.dirname(sys.argv[0])
        if scriptdir in sys.path:
            sys.path.remove(scriptdir)
        sys.path.insert(0, '.')
    
    if len(sys.argv) <= 2:
        for arg in sys.argv[1:]:
            if ispath(arg) and os.path.exists(arg):
                arg = importfile(arg)
            try:
                #pprint.pprint(struct_code(arg))
                print json.dumps(struct_code(arg))
            except ImportError, err:
                print err
    else:
        cmd = os.path.basename(sys.argv[0])
        print """pycode.py - python code analysis

%s <name> ...
    <name> may be the name of a Python function, module, or package, 
    or a dotted reference to a class or function within a module or 
    module in a package.""" % cmd

if __name__ == '__main__':
    cli()    		
