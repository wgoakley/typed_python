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

from typed_python.compiler.typed_expression import TypedExpression
from typed_python.compiler.type_wrappers.refcounted_wrapper import RefcountedWrapper
from typed_python.compiler.type_wrappers.bound_compiled_method_wrapper import BoundCompiledMethodWrapper
import typed_python.compiler.type_wrappers.runtime_functions as runtime_functions

from typed_python import NoneType

import typed_python.compiler.native_ast as native_ast
import typed_python.compiler


typeWrapper = lambda x: typed_python.compiler.python_object_representation.typedPythonTypeToTypeWrapper(x)


def cell_get(cell):
    if not cell.isSet():
        raise RuntimeError("Cell is empty")
    return cell.getUnsafe()


def cell_set(cell, val):
    if cell.isSet():
        cell.destroyUnsafe()

    cell.initializeUnsafe(val)


def cell_clear(cell):
    if cell.isSet():
        cell.destroyUnsafe()


class TypedCellWrapper(RefcountedWrapper):
    is_pod = False
    is_empty = False
    is_pass_by_ref = True

    BYTES_BEFORE_INIT_BITS = 16  # the refcount and vtable are both 8 byte integers.

    def __init__(self, t):
        super().__init__(t)

        element_types = [('refcount', native_ast.Int64), ('initialized', native_ast.Int64), ('data', native_ast.UInt8)]

        self.layoutType = native_ast.Type.Struct(element_types=element_types, name=t.__qualname__+"Layout").pointer()

    def convert_default_initialize(self, context, instance):
        return context.pushException(TypeError, f"Can't default initialize instances of {self}")

    def getNativeLayoutType(self):
        return self.layoutType

    def on_refcount_zero(self, context, instance):
        assert instance.isReference

        return (
            context.converter.defineNativeFunction(
                "destructor_" + str(self.typeRepresentation),
                ('destructor', self),
                [self],
                typeWrapper(NoneType),
                self.generateNativeDestructorFunction
            )
            .call(instance)
        )

    def generateNativeDestructorFunction(self, context, out, inst):
        self.refHeld(inst).convert_destroy()

        context.pushEffect(
            runtime_functions.free.call(inst.nonref_expr.cast(native_ast.UInt8Ptr))
        )

    def refHeld(self, instance):
        return TypedExpression(
            instance.context,
            instance.nonref_expr.ElementPtrIntegers(0, 2).cast(
                typeWrapper(self.typeRepresentation.HeldType).getNativeLayoutType().pointer()
            ),
            typeWrapper(self.typeRepresentation.HeldType),
            True
        )

    def isInitialized(self, instance):
        return TypedExpression(
            instance.context,
            instance.nonref_expr.ElementPtrIntegers(0, 1),
            typeWrapper(int),
            True
        )

    def convert_method_call(self, context, instance, methodName, args, kwargs):
        if methodName == "get" and not args and not kwargs:
            return context.call_py_function(cell_get, (instance,), {})

        if methodName == "set" and len(args) == 1 and not kwargs:
            return context.call_py_function(cell_set, (instance, args[0]), {})

        if methodName == "clear" and not args and not kwargs:
            return context.call_py_function(cell_clear, (instance,), {})

        if methodName == "isSet" and not args and not kwargs:
            return self.isInitialized(instance).convert_bool_cast()

        if methodName == "getUnsafe" and not args and not kwargs:
            return self.refHeld(instance)

        if methodName == "initializeUnsafe" and len(args) == 1 and not kwargs:
            arg = args[0].convert_to_type(self.typeRepresentation.HeldType, explicit=True)
            if arg is None:
                return None

            self.refHeld(instance).convert_copy_initialize(arg)
            self.isInitialized(instance).convert_copy_initialize(context.constant(1))
            return context.constant(None)

        if methodName == "destroyUnsafe" and not args and not kwargs:
            self.refHeld(instance).convert_destroy()
            return context.constant(None)

        return super().convert_method_call(context, instance, methodName, args, kwargs)

    def convert_attribute(self, context, expr, attr):
        if attr in ("get", "isSet", "clear", "set", "getUnsafe", "initializeUnsafe", "destroyUnsafe"):
            return expr.changeType(BoundCompiledMethodWrapper(self, attr))

        return super().convert_attribute(context, expr, attr)
