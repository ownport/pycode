import sys
if '' not in sys.path:
    sys.path.append('')

import json
import pycode
import pprint
import unittest


class PyCodeStructTests(unittest.TestCase):

    def test_render_code(self):    
        result = {
                    'description': 'built-in function dir',
                    'module': '__builtin__',
                    'name': 'dir',
                    'object': ('function', 'dir'),
                    'struct': {'dir(...)': 'The most base type'}
        }
        self.assertEqual(pycode.render_code('dir'), result)
    
    def test_struct(self):
    
        class obj(object):
            ''' test class obj '''
            pass
    
        s = pycode.PyCodeStruct()
        obj_struct = s.struct(obj)
        self.assertIn('obj', obj_struct)
        self.assertEqual(obj_struct['obj']['doc'], 'test class obj')
        pprint.pprint(obj_struct)
        
    def test_struct_multi_inherited(self):
    
        class A(object):
            ''' test class A '''
            def method_a(self):
                ''' method A '''
                pass

        class B(object):
            ''' test class B '''
            def method_b(self):
                ''' method B '''
                pass

        class C(A,B):
            ''' test class C (inherited A & B)'''
            def method_c(self):
                ''' method C '''
                pass

        s = pycode.PyCodeStruct()
        struct_c = s.struct(C)
        self.assertEqual(struct_c['C']['bases'], ['A', 'B'])
        pprint.pprint(struct_c)
        
        
if __name__ == '__main__':
    unittest.main()        

