#   Copyright 2017-2020 typed_python Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import unittest
from typed_python import Function, NamedTuple, bytecount
from typed_python.compiler.runtime import RuntimeEventVisitor, Entrypoint


class DidCompileVisitor(RuntimeEventVisitor):
    def __init__(self):
        super().__init__()

        self.didCompile = False

    def onNewFunction(self, f, inputTypes, outputType, variables):
        self.didCompile = True


class TestCompilingClosures(unittest.TestCase):
    def test_lambda_with_same_code_doesnt_retrigger_compile(self):
        def makeAdder():
            def add(x, y):
                return x + y
            return add

        @Entrypoint
        def callFun(f, x, y):
            return f(x, y)

        vis = DidCompileVisitor()

        with vis:
            self.assertEqual(callFun(makeAdder(), 1, 2), 3)

        self.assertTrue(vis.didCompile)

        vis = DidCompileVisitor()

        with vis:
            self.assertEqual(callFun(makeAdder(), 1, 2), 3)

        # the second time, the code for the adder should have been the same, so
        # we shouldn't have triggered compilation.
        self.assertFalse(vis.didCompile)

    def test_capture_int_type(self):
        x = 10

        def f():
            return x

        fAsFun = Function(f)

        self.assertTrue(fAsFun.overloads[0].closureType == NamedTuple(x=int))

        pyFun = fAsFun.extractPyFun(0)

        self.assertEqual(pyFun(), 10)
        self.assertEqual(f(), 10)
        self.assertEqual(fAsFun(), 10)

        # Function objects capture variables when the object is created,
        # instead of retaining a handle to the parent function. This is
        # different than standard python semantics, but necessary to allow
        # typing to be stable (and therefore fast)
        x = 20
        self.assertEqual(f(), 20)
        self.assertEqual(fAsFun(), 10)

    def test_capture_unassigned_variable_fails(self):
        with self.assertRaisesRegex(TypeError, "free variable 'x' referenced before assignment in enclosing scope"):
            @Function
            def f():
                return x

        # we have to have this so that 'x' is not a globally scoped
        # variable.
        x = 10

    def test_closure_types(self):
        def makeReturnX():
            @Function
            def f():
                return x
            return f

        x = 10
        return10 = makeReturnX()

        x = 20
        return20 = makeReturnX()

        x = "hi"
        returnHi = makeReturnX()

        self.assertEqual(return10(), 10)
        self.assertEqual(return20(), 20)
        self.assertEqual(returnHi(), "hi")

        self.assertEqual(type(return10), type(return20))
        self.assertNotEqual(type(return10), type(returnHi))

    def test_closure_grabbing_types(self):
        T = int

        @Function
        def f(x):
            return T(x)

        pf = f.extractPyFun(0)
        self.assertEqual(pf.__closure__[0].cell_contents, T)
        self.assertEqual(f(1.5), 1)
        self.assertEqual(bytecount(f.overloads[0].closureType), 0)

    def test_closure_grabbing_closures(self):
        x = 10

        @Function
        def f():
            return x

        @Function
        def g():
            return f()

        self.assertEqual(g(), x)

    def test_calling_closure_with_bound_args(self):
        x = 10
        @Function
        def f(y):
            return y + x

        @Entrypoint
        def callIt(arg):
            return f(arg)

        self.assertEqual(callIt(20), 30)
