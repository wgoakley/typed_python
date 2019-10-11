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
import typed_python.compiler.native_ast as native_ast
import typed_python.compiler
from typed_python import String, Value


class PythonFreeObjectWrapper(Wrapper):
    """Wraps an arbitrary python object we don't know how to convert.

    Practically speaking, this object can't do anything except interact
    in the type layer. But if we access its attributes or call it with other
    type-like objects, we can resolve them."""

    is_pod = True
    is_empty = True
    is_pass_by_ref = False
    is_compile_time_constant = True

    def __init__(self, f):
        super().__init__(Value(f))

    def getNativeLayoutType(self):
        return native_ast.Type.Void()

    def getCompileTimeConstant(self):
        return self.typeRepresentation.Value

    def convert_bin_op(self, context, left, op, right, inplace):
        if right.expr_type == self:
            if op.matches.Eq or op.matches.Is:
                return context.constant(True)
            if op.matches.NotEq or op.matches.IsNot:
                return context.constant(False)

        return super().convert_bin_op(context, left, op, right, inplace)

    def convert_call(self, context, left, args, kwargs):
        if all(
            [x.expr_type.is_compile_time_constant for x in list(args) + list(kwargs.values())]
        ):
            try:
                return typed_python.compiler.python_object_representation.pythonObjectRepresentation(
                    context,
                    self.typeRepresentation.Value(
                        *[a.expr_type.getCompileTimeConstant() for a in args],
                        **{k: v.expr_type.getCompileTimeConstant() for k, v in kwargs.items()},
                    ),
                )
            except Exception as e:
                context.pushException(type(e), str(e))
                return

        return context.call_py_function(self.typeRepresentation.Value, args, kwargs)

    def convert_attribute(self, context, instance, attribute):
        try:
            return typed_python.compiler.python_object_representation.pythonObjectRepresentation(
                context, getattr(self.typeRepresentation.Value, attribute)
            )
        except Exception as e:
            context.pushException(type(e), str(e))
            return

    def convert_to_type_with_target(self, context, e, targetVal, explicit):
        target_type = targetVal.expr_type

        if not explicit:
            return super().convert_to_type_with_target(context, e, targetVal, explicit)

        if target_type.typeRepresentation == String:
            targetVal.convert_copy_initialize(
                context.constant(str(self.typeRepresentation.Value))
            )
            return context.constant(True)

        return super().convert_to_type_with_target(context, e, targetVal, explicit)
