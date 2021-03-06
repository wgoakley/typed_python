#   Copyright 2017-2019 typed_python Authors
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

from typed_python import Tuple, NamedTuple, Class, Member, ListOf, Compiled
import typed_python._types as _types
import unittest
from typed_python import Entrypoint, makeNamedTuple


class TestTupleCompilation(unittest.TestCase):
    def test_tuple_passing(self):
        T = Tuple(float, int, str)

        @Compiled
        def f(x: T) -> T:
            y = x
            return y

        t = T((0.0, 1, "hi"))
        self.assertEqual(f(t), t)

    def test_named_tuple_passing(self):
        NT = NamedTuple(a=float, b=int, c=str)

        @Compiled
        def f(x: NT) -> NT:
            y = x
            return y

        nt = NT(a=0.0, b=1, c="hi")
        self.assertEqual(f(nt), nt)

    def test_named_tuple_getattr(self):
        NT = NamedTuple(a=float, b=int, c=str)

        @Compiled
        def f(x: NT) -> str:
            return x.c + x.c

        nt = NT(a=0.0, b=1, c="hi")
        self.assertEqual(f(nt), "hihi")

    def test_named_tuple_assignment_refcounting(self):
        class C(Class):
            x = Member(int)

        NT = NamedTuple(c=C)

        @Compiled
        def f(x: NT):
            y = x
            return y.c

        c = C(x=20)
        res = f(NT(c=c))

        self.assertEqual(res.x, 20)
        self.assertEqual(_types.refcount(res), 2)

    def test_indexing(self):
        T = Tuple(int, str)

        @Entrypoint
        def getFirst(t):
            return t[0]

        @Entrypoint
        def getSecond(t):
            return t[1]

        @Entrypoint
        def getIx(t, i):
            return t[i]

        self.assertEqual(getFirst(T((1, '2'))), 1)
        self.assertEqual(getSecond(T((1, '2'))), '2')

        self.assertEqual(getIx(T((1, '2')), 0), 1)
        self.assertEqual(getIx(T((1, '2')), 1), '2')

    def test_iterating(self):
        @Entrypoint
        def tupToString(x):
            res = ListOf(str)()
            for elt in x:
                res.append(str(elt))
            return res

        self.assertEqual(
            tupToString(Tuple(int, str)((0, 'a'))),
            ["0", "a"]
        )

    def test_named_tuple_replacing_error(self):
        """We should have errors for all the field names passed to the replacing function,
        if the fields are not in the tuple definition.
        """
        NT = NamedTuple(a=int, b=str)
        n1 = NT(a=1, b='x')

        @Compiled
        def f1(x: NT) -> NT:
            return x.replacing(c=10)

        with self.assertRaisesRegex(Exception, "The arguments list contain names 'c' which are not in the tuple definition."):
            f1(n1)

        @Compiled
        def f2(x: NT) -> NT:
            return x.replacing(c=10, d=10, e=10)

        with self.assertRaisesRegex(Exception, "The arguments list contain names 'c, d, e' which are not in the tuple definition."):
            f2(n1)

    def test_named_tuple_replacing_function(self):
        NT = NamedTuple(a=int, b=str)
        n1 = NT(a=1, b='x')

        @Compiled
        def f1(x: NT, a: int) -> NT:
            return x.replacing(a=a)

        n2 = f1(n1, 10)
        self.assertIsNot(n1, n2)
        self.assertEqual(n2.a, 10)
        self.assertEqual(n2.b, 'x')

        @Compiled
        def f2(x: NT, a: int, b: str) -> NT:
            return x.replacing(a=a, b=b)

        n3 = f2(n2, 123, '345')
        self.assertIsNot(n1, n2)
        self.assertIsNot(n2, n3)
        self.assertEqual(n3.a, 123)
        self.assertEqual(n3.b, '345')

    def test_named_tuple_replacing_refcount(self):
        N = NamedTuple(x=ListOf(int))
        N = NamedTuple(x=ListOf(int))
        aList = ListOf(int)([1, 2, 3])

        self.assertEqual(_types.refcount(aList), 1)
        nt = N().replacing(x=aList)
        self.assertEqual(nt.x, aList)
        self.assertEqual(_types.refcount(aList), 2)
        nt = None
        self.assertEqual(_types.refcount(aList), 1)

    def test_named_tuple_construction(self):
        NT = NamedTuple(x=ListOf(int), y=float)

        @Entrypoint
        def makeNt():
            return NT()

        @Entrypoint
        def makeNtX(x):
            return NT(x=x)

        @Entrypoint
        def makeNtY(y):
            return NT(y=y)

        @Entrypoint
        def makeNtXY(x, y):
            return NT(x=x, y=y)

        self.assertEqual(makeNt(), NT())
        self.assertEqual(makeNtX(ListOf(int)([1, 2, 3])), NT(x=[1, 2, 3]))
        self.assertEqual(makeNtXY(ListOf(int)([1, 2, 3]), 2.0), NT(x=[1, 2, 3], y=2.0))
        self.assertEqual(makeNtY(2.0), NT(y=2.0))

        with self.assertRaisesRegex(TypeError, "convert from type Float64 to type List"):
            makeNtX(1.2)

    def test_compile_make_named_tuple(self):
        @Entrypoint
        def makeNt(x, y):
            return makeNamedTuple(x=x, y=y)

        self.assertEqual(makeNt(1, 2), makeNamedTuple(x=1, y=2))
        self.assertEqual(makeNt(1, "2"), makeNamedTuple(x=1, y="2"))

    def test_compiled_tuple_construction(self):
        def makeNamed(x, y):
            return NamedTuple(x=type(x), y=type(y))((x, y))

        def makeUnnamed(x, y):
            return Tuple(type(x), type(y))((x, y))

        def check(f, x, y):
            compiledRes = Entrypoint(f)(x, y)
            interpRes = f(x, y)

            self.assertEqual(compiledRes, interpRes)
            self.assertEqual(type(compiledRes), type(interpRes))

        check(makeNamed, 1, 2)
        check(makeNamed, 1, "2")
        check(makeUnnamed, 1, 2)
        check(makeUnnamed, 1, "2")
