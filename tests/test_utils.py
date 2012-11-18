import sys
if '' not in sys.path:
    sys.path.append('')

import types
import pycode
import pprint
import unittest


class PyCodeUtilsTests(unittest.TestCase):
    
    def test_importfile(self):
    
        self.assertEqual(type(pycode.importfile('./pycode.py')), types.ModuleType)

    def test_safeimport(self):

        self.assertEqual(type(pycode.safeimport('os')), types.ModuleType)
        self.assertEqual(type(pycode.safeimport('os.path')), types.ModuleType)
        self.assertEqual(type(pycode.safeimport('pycode')), types.ModuleType)

    def test_locate(self):
    
        self.assertEqual(pycode.locate('dir'), dir)
        self.assertEqual(pycode.locate('object'), object)
        self.assertEqual(type(pycode.locate('os')), types.ModuleType)
        self.assertEqual(type(pycode.locate('pycode')), types.ModuleType)
        self.assertEqual(type(pycode.locate('pycode.struct_code')), types.FunctionType)

    def test_resolve_by_str(self):
        
        self.assertEqual(pycode.resolve('dir'), (dir, 'dir'))
        self.assertEqual(pycode.resolve('object'), (object, 'object'))

    def test_resolve_by_object(self):
    
        def t1():
            pass        
        self.assertEqual(pycode.resolve(t1), (t1, 't1'))

    def test_describe_simple(self):
        
        self.assertEqual(pycode.describe(types),('module', 'types'))
        self.assertEqual(pycode.describe(dir),('built-in function', 'dir'))

    def test_describe_builtin(self):

        import __builtin__
        self.assertEqual(pycode.describe(__builtins__),('built-in module', '__builtin__'))

    def test_describe_package(self):

        import tests
        self.assertEqual(pycode.describe(tests),('package', 'tests'))

    def test_describe_class(self):

        class T1(object):
            def get(self):
                pass
        self.assertEqual(pycode.describe(T1),('class', 'T1'))
        self.assertEqual(pycode.describe(T1.get),('method', 'get'))
        
    def test_describe_function(self):

        def f1():
            pass
        self.assertEqual(pycode.describe(f1),('function', 'f1'))

        
    def test_struct_code_dir(self):
        
        #pprint.pprint(pycode.struct_code('dir'))
        #pprint.pprint(pycode.struct_code('os.path'))
        #pprint.pprint(pycode.struct_code('os.path.join'))
        pass
        
if __name__ == '__main__':
    unittest.main()        

