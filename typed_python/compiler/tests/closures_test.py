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
import time
from typed_python import Function, NamedTuple, bytecount, ListOf, DisableCompiledCode
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

    def test_passing_closures_as_arguments(self):
        x = 10
        @Function
        def f(y):
            return y + x

        @Entrypoint
        def callIt(f, arg):
            return f(arg)

        self.assertEqual(callIt(f, 20), 30)

    def test_calling_closures_perf(self):
        ct = 100000

        aList1 = ListOf(int)([])

        def makeAppender(l):
            @Function
            def append(y):
                l.append(y)
            return append

        @Entrypoint
        def callManyTimes(c1, ct):
            for i in range(ct):
                c1(i)

        callManyTimes(makeAppender(aList1), ct)

        aList1.clear()

        t0 = time.time()
        callManyTimes(makeAppender(aList1), ct)
        t1 = time.time()

        aList1.clear()

        elapsedCompiled = t1 - t0

        with DisableCompiledCode():
            t0 = time.time()
            callManyTimes(makeAppender(aList1), ct)
            t1 = time.time()

        elapsedNoncompiled = t1 - t0

        aList1 = []

        def makeAppender(l):
            def append(y):
                l.append(y)
            return append

        def alternatingCall(c1, c2, ct):
            for i in range(ct):
                c1(i)

        t0 = time.time()
        callManyTimes(makeAppender(aList1), ct)
        t1 = time.time()

        elapsedNontyped = t1 - t0

        print(elapsedCompiled, elapsedNoncompiled, elapsedNontyped)

        print(elapsedNontyped / elapsedCompiled, " times faster")
        # for me, the compiled form is about 280 times faster than the uncompiled form
        self.assertTrue(elapsedCompiled * 50 < elapsedNontyped)

    def test_assigning_closures_as_values(self):
        ct = 100000

        aList1 = ListOf(int)([])
        aList2 = ListOf(int)([])

        def makeAppender(l):
            @Function
            def append(y):
                l.append(y)
            return append

        @Entrypoint
        def alternatingCall(c1, c2, ct):
            for i in range(ct):
                c1(i)
                temp = c1
                c1 = c2
                c2 = temp

        c1 = makeAppender(aList1)
        c2 = makeAppender(aList2)

        self.assertEqual(type(c1), type(c2))

        alternatingCall(c1, c2, ct)

        self.assertEqual(len(aList1), ct // 2)
        self.assertEqual(len(aList2), ct // 2)

        aList1.clear()
        aList2.clear()

        t0 = time.time()
        alternatingCall(c1, c2, ct)
        t1 = time.time()

        aList1.clear()
        aList2.clear()

        elapsedCompiled = t1 - t0

        with DisableCompiledCode():
            t0 = time.time()
            alternatingCall(c1, c2, ct)
            t1 = time.time()

        # elapsedNoncompiled = t1 - t0

        aList1 = []
        aList2 = []

        def makeAppender(l):
            def append(y):
                l.append(y)
            return append

        def alternatingCall(c1, c2, ct):
            for i in range(ct):
                c1(i)
                temp = c1
                c1 = c2
                c2 = temp

        c1 = makeAppender(aList1)
        c2 = makeAppender(aList2)

        t0 = time.time()
        alternatingCall(c1, c2, ct)
        t1 = time.time()

        elapsedNontyped = t1 - t0

        # for me, elapsedCompiled is 3x faster than elapsedNontyped, but
        # elapsedNoncompiled is about 5x slower than elapsedNontyped, because
        # typed python is not very efficient yet as an interpreter.
        # there is a _lot_ of overhead in repeatedly swapping because we
        # end up increffing the contained list many many times.
        self.assertTrue(elapsedCompiled * 2 < elapsedNontyped)

    def test_closure_in_listof(self):
        def makeAdder(x):
            @Function
            def f(y):
                return x + y
            return f

        self.assertEqual(type(makeAdder(10)), type(makeAdder(20)))

        T = ListOf(type(makeAdder(10)))

        aList = T()
        aList.append(makeAdder(1))
        aList.append(makeAdder(2))

        def callEachItemManyTimes(l, times):
            res = 0
            for count in range(times):
                for item in l:
                    res = item(res)
            return res

        resUncompiled = callEachItemManyTimes(aList, 10)

        resCompiled = Entrypoint(callEachItemManyTimes)(aList, 10)

        self.assertEqual(resUncompiled, resCompiled)

    def test_closure_distinguishes_assigned_variables(self):
        # f relies on 'x', but since 'x' is only assigned exactly once, we
        # can assume the value doesn't change type and bind its value
        # directly in the closure.
        x = 10
        def f():
            return x

        # g relies on 'y' but because the value is assigned more
        # than once in the function, we bind it with an untyped cell.
        # if we pass it into an entrypoint.
        y = 10
        def g():
            return y
        y = 20

        assert False, 'test something for real'

    def test_closure_reads_variables_ahead(self):
        @Function
        def f():
            return g()

        # at this point, 'f's type is not yet set, because we don't know
        # what 'g' is going to be. We can see that it will be assigned exactly once,
        # but we don't know the value until it gets assigned.
        # as a result, 'f' will have 'UnresolvedFunction'. An UnresolvedFunction
        # never makes its way into any typedpython datastructures - we always force
        # it to resolve when it gets used (and that resolution will bind to the cell
        # as an untyped value if its not bound already)

        def g():
            return 10

        # because we don't use 'f' before 'g' is bound, 'f' is able
        # to resolve its type
        self.assertEqual(f(), 10)


# things in play:
# 1. have we marked it with a Function?
# 2. can we tell which of its closure values will be stable through time?
# 3. how can its type be known at creation if not all closure values are set yet?
#    it's a PyFunctionInstance. _we can change its type_!!
