#   Copyright 2019 typed_python Authors
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

from typed_python.compiler.type_wrappers.wrapper import Wrapper
from typed_python.compiler import native_ast

import typed_python


class CompilableBuiltin(Wrapper):
    """Base class for Wrappers that expose _themselves_.

    We use this class to easily create constants that can generate code in the
    converter.

    For instance,

    class SomeCodeGenerator(CompilableBuiltin):
        def convert_call(self, context, instance, args, kwargs):
            ...

    def someFunctionThatIsNativeCompiledOnly(x):

        ...
        # this will dispatch to the 'convert_call' above.
        return SomeCodeGenerator()(x)
    """
    is_pod = True
    is_empty = True
    is_pass_by_ref = False
    is_compile_time_constant = True

    def __init__(self):
        super().__init__(self)

    def getNativeLayoutType(self):
        return native_ast.Type.Void()

    def __eq__(self, other):
        raise NotImplementedError(self)

    @property
    def __name__(self):
        return str(self)

    def __hash__(self):
        raise NotImplementedError(self)

    def __str__(self):
        return type(self).__qualname__

    def __repr__(self):
        return type(self).__qualname__

    @classmethod
    def convert_type_call(cls, context, typeInst, args, kwargs):
        if all(a.expr_type.is_compile_time_constant for a in args):
            tw = cls(*[a.expr_type.getCompileTimeConstant() for a in args])

            return typed_python.compiler.python_object_representation.pythonObjectRepresentation(context, tw)

        raise Exception("Can't convert this")
