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
