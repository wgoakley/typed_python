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
from typed_python import Function, NamedTuple, bytecount, ListOf, DisableCompiledCode, TypedCell, Forward, PyCell
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

    def test_mutually_recursive_closures(self):
        @Function
        def f(x):
            if x == 0:
                return 0
            return g(x-1)

        @Function
        def g(x):
            return f(x-1)

        self.assertEqual(f.overloads[0].closureType.ElementNames[0], 'g')
        self.assertEqual(f.overloads[0].closureType.ElementTypes[0], PyCell)

        self.assertEqual(f(10), 0)

    def test_typed_cell(self):
        T = TypedCell(int)

        t = T()

        self.assertFalse(t.isSet())

        with self.assertRaises(TypeError):
            t.set("hi")

        with self.assertRaises(Exception):
            t.get()

        t.set(10)

        self.assertTrue(t.isSet())

        self.assertEqual(t.get(), 10)

        t.clear()

        self.assertFalse(t.isSet())

        with self.assertRaises(Exception):
            t.get()

    def test_typed_cell_in_tuple(self):
        TC = TypedCell(int)

        aTup = NamedTuple(x=TC)(x=TC())
        aTup.x.set(1)

    def test_typed_cell_with_forwards(self):
        Tup = Forward("Tup")
        Tup = Tup.define(NamedTuple(cell=TypedCell(Tup), x=int))
        TC = TypedCell(Tup)

        self.assertEqual(Tup.ElementTypes[0], TC)

        t1 = Tup(cell=TC(), x=1)
        t2 = Tup(cell=TC(), x=2)
        t1.cell.set(t2)
        t2.cell.set(t1)

        self.assertEqual(t1.cell.get().x, 2)
        self.assertEqual(t2.cell.get().x, 1)
        self.assertEqual(t1.cell.get().cell.get().x, 1)
        self.assertEqual(t2.cell.get().cell.get().x, 2)

    def test_function_overload_with_closures(self):
        @Function
        def f():
            return x

        @f.overload
        def f(anArg):
            return y

        @Function
        def f2(anArg, anArg2):
            return z

        @f2.overload
        def f2(anArg, anArg2, anArg3):
            return w

        x = 10
        y = 20
        z = 30
        w = 40

        self.assertEqual(f(), 10)
        self.assertEqual(f(1), 20)

        self.assertEqual(f2(1, 2), 30)
        self.assertEqual(f2(1, 2, 3), 40)

        combo = f.overload(f2)

        self.assertEqual(combo(), 10)
        self.assertEqual(combo(1), 20)
        self.assertEqual(combo(1, 2), 30)
        self.assertEqual(combo(1, 2, 3), 40)

    def test_replace_function_closure(self):
        @Function
        def f():
            return x

        @f.overload
        def f(anArg):
            return y

        x = 10
        y = 20

        fRep = f.replaceClosure(1, NamedTuple(y=int)(y=2))

        self.assertEqual(f(), 10)
        self.assertEqual(f(1), 20)

        self.assertEqual(fRep(), 10)
        self.assertEqual(fRep(1), 2)

        fRep2 = fRep.replaceClosure(0, NamedTuple(x=str)(x="hihi"))

        self.assertEqual(fRep2(), "hihi")
        self.assertEqual(fRep2(1), 2)

        # verify we can put it back to pointing at our original pycells
        fRep3 = (
            fRep2
            .replaceClosure(0, f.closureForOverload(0))
            .replaceClosure(1, f.closureForOverload(1))
        )

        self.assertEqual(fRep3(), 10)
        self.assertEqual(fRep3(1), 20)

    def test_compile_typed_closure(self):
        @Entrypoint
        def f(count):
            res = 0.0

            for i in range(count):
                res = res + x

            return res

        x = 0

        xCell = TypedCell(float)()
        xCell.set(1.0)

        fWithTypedClosure = f.replaceClosure(0, NamedTuple(x=TypedCell(float))(x=xCell))

        self.assertEqual(fWithTypedClosure(10), 10.0)

        t0 = time.time()
        fWithTypedClosure(1000000)
        elapsed = time.time() - t0

        print("Took ", elapsed, " to do 1mm typed cell lookups")

        # I get about 0.0024, or 400mm lookups a second. If we were
        # to allow it to assume the closure is populated, which we should be
        # able to do in many cases, this would be more like 1bb lookups.
        self.assertTrue(elapsed < 0.2)

    def test_build_mutually_recursive_functions_from_untyped_closure(self):
        @Entrypoint
        def f(x):
            if x > 0:
                return g(x - 1) + 1.0
            return 0.0

        @Entrypoint
        def g(x):
            return f(x)

        # explicitly build the typed closure
        fType = Forward("fType")
        gType = Forward("gType")

        fType = fType.define(
            type(f).replaceClosureType(
                0,
                NamedTuple(g=TypedCell(gType))
            )
        )

        gType = gType.define(
            type(g).replaceClosureType(
                0,
                NamedTuple(f=TypedCell(fType))
            )
        )

        gCell = TypedCell(gType)()
        fCell = TypedCell(fType)()

        fCell.set(f.replaceClosure(0, NamedTuple(g=TypedCell(gType))(g=gCell)))
        gCell.set(g.replaceClosure(0, NamedTuple(f=TypedCell(fType))(f=fCell)))

        self.assertEqual(fCell.get()(100), 100.0)

    def test_call_function_in_closure_perf(self):
        @Entrypoint
        def f(x):
            return x + 1.0

        @Entrypoint
        def g(x, times):
            res = 0.0
            for i in range(times):
                res += f(x)
            return res

        fCell = TypedCell(type(f))()
        fCell.set(f)

        g = g.replaceClosure(0, NamedTuple(f=type(fCell))(f=fCell))

        g(1.0, 1000000)

        t0 = time.time()
        g(1.0, 1000000)
        elapsed = time.time() - t0

        print("took ", elapsed, " to do 1mm dispatches through a TypedCell")
