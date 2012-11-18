import sys
if '' not in sys.path:
    sys.path.append('')

import types
import pycode
import pprint
import unittest

class A(object):
    ''' Class A '''
    def method1(self,a):
        ''' A.method1() '''
        pass

class B(A):
    ''' Class B '''
    def method2(self,b):
        ''' B.method2() '''
        pass

class C(object):
    ''' Class C '''
    pass

class D(B,C):
    ''' Class D '''
    pass

class PyCodeStructTests(unittest.TestCase):

    def test_struct_code_lambda(self):
        
        result = {  
            'decl': '<lambda>x', 
            'doc': '', 
            'name': '<lambda>', 
            'type': 'function'
        }
        f = lambda x: x
        code = pycode.PyCodeStruct()
        self.assertEqual(code.struct(f), result)

    def test_struct_code_func(self):
        
        code = pycode.PyCodeStruct()
        struct_dir = code.struct(dir)
        self.assertEqual(struct_dir['name'], 'dir')
        self.assertEqual(struct_dir['type'], 'built-in function')
        self.assertEqual(struct_dir['decl'], 'dir(...)')
        self.assertTrue(len(struct_dir['doc']) > 1)

    def test_struct_code_class_A(self):
        
        code = pycode.PyCodeStruct()
        struct_class = code.struct(A)
        self.assertEqual(struct_class['name'], 'A')
        self.assertEqual(struct_class['type'], 'class')
        self.assertEqual(struct_class['bases'], ['__builtin__.object'])
        self.assertEqual(struct_class['doc'], 'Class A')
        self.assertEqual(len(struct_class['class_attrs']), 3)
        for attrs in struct_class['class_attrs']:
            self.assertIn(attrs['name'], ['__dict__', '__weakref__', 'method1'])

    def test_struct_code_class_BA(self):
                
        code = pycode.PyCodeStruct()
        struct_class = code.struct(B)
        self.assertEqual(struct_class['name'], 'B')
        self.assertEqual(struct_class['type'], 'class')
        self.assertEqual(struct_class['bases'], ['A', '__builtin__.object'])
        self.assertEqual(struct_class['doc'], 'Class B')
        self.assertEqual(len(struct_class['class_attrs']), 1)
        for attrs in struct_class['class_attrs']:
            self.assertIn(attrs['name'], ['method2'])

    def test_struct_code_class_D(self):

        code = pycode.PyCodeStruct()
        struct_class = code.struct(D)
        self.assertEqual(struct_class['name'], 'D')
        self.assertEqual(struct_class['type'], 'class')
        self.assertEqual(struct_class['bases'], ['B', 'A', 'C', '__builtin__.object'])
        self.assertEqual(struct_class['doc'], 'Class D')
        self.assertEqual(len(struct_class['class_attrs']), 0)

    def test_struct_module_os(self):
        
        os_module = pycode.locate('os')
        code = pycode.PyCodeStruct()
        struct_os = code.struct(os_module)
        self.assertEqual(struct_os['doc_location'], 'http://docs.python.org/library/os')
        #pprint.pprint(struct_os)

    def test_struct_module_pycode(self):
        
        pycode_module = pycode.locate('pycode')
        code = pycode.PyCodeStruct()
        struct_pycode = code.struct(pycode_module)
        #self.assertEqual(struct_pycode['name'], 'pycode')
        #self.assertIn('file', struct_pycode)
        #self.assertIn('doc', struct_pycode)
        #pprint.pprint(struct_pycode)
        
if __name__ == '__main__':
    unittest.main()        

