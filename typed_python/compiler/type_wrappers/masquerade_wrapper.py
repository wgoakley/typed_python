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

import typed_python

from typed_python.compiler.type_wrappers.wrapper import Wrapper

typeWrapper = lambda t: typed_python.compiler.python_object_representation.typedPythonTypeToTypeWrapper(t)


class MasqueradeWrapper(Wrapper):
    """Base class for a TypedPython type masquerading as an interpreter type.

    By default all operations force us to convert to the interpreter form and then
    try it there. Subclasses should override if they have a better idea.
    """
    def __str__(self):
        return f"Masquerade({self.typeRepresentation} as {self.interpreterTypeRepresentation})"

    @property
    def interpreterTypeRepresentation(self):
        """The type we're masquerading as."""
        raise NotImplementedError("Subclasses implement")

    def getNativeLayoutType(self):
        return typeWrapper(self.typeRepresentation).getNativeLayoutType()

    def convert_mutable_masquerade_to_untyped_type(self):
        raise NotImplementedError("Subclasses implement")

    def convert_mutable_masquerade_to_untyped(self, context, instance):
        raise NotImplementedError("Subclasses implement")

    def convert_masquerade_to_untyped(self, context, instance):
        raise NotImplementedError("Subclasses implement")

    def convert_masquerade_to_typed(self, context, instance):
        return instance.changeType(self.typeRepresentation)

    def convert_to_type_with_target(self, context, e, targetVal, explicit):
        # Allow the typed form of the object to perform the conversion
        return e.convert_masquerade_to_typed().convert_to_type_with_target(targetVal, explicit)

    def get_iteration_expressions(self, context, instance):
        return instance.convert_masquerade_to_typed().get_iteration_expressions()

    def convert_incref(self, context, instance):
        return typeWrapper(self.typeRepresentation).convert_incref(
            context,
            instance.convert_masquerade_to_typed()
        )

    def convert_assign(self, context, target, toStore):
        return typeWrapper(self.typeRepresentation).convert_assign(
            context,
            target.convert_masquerade_to_typed(),
            toStore.convert_masquerade_to_typed()
        )

    def convert_copy_initialize(self, context, target, toStore):
        return typeWrapper(self.typeRepresentation).convert_copy_initialize(
            context,
            target.convert_masquerade_to_typed(),
            toStore.convert_masquerade_to_typed()
        )

    def convert_destroy(self, context, instance):
        return typeWrapper(self.typeRepresentation).convert_destroy(
            context,
            instance.convert_masquerade_to_typed()
        )

    def convert_default_initialize(self, context, target):
        raise Exception("This should never be called")

    def convert_next(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_next()

    def convert_attribute(self, context, instance, attribute):
        return instance.convert_masquerade_to_untyped().convert_attribute(attribute)

    def convert_set_attribute(self, context, instance, attribute, value):
        return instance.convert_masquerade_to_untyped().convert_set_attribute(attribute, value)

    def convert_delitem(self, context, instance, item):
        return instance.convert_masquerade_to_untyped().convert_delitem(item)

    def convert_getitem(self, context, instance, item):
        return instance.convert_masquerade_to_untyped().convert_getitem(item)

    def convert_getslice(self, context, instance, lower, upper, step):
        return instance.convert_masquerade_to_untyped().convert_getslice(lower, upper, step)

    def convert_setitem(self, context, instance, index, value):
        return instance.convert_masquerade_to_untyped().convert_setitem(index, value)

    def convert_call(self, context, instance, args, kwargs):
        return instance.convert_masquerade_to_untyped().convert_call(args, kwargs)

    def convert_len(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_len()

    def convert_hash(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_hash()

    def convert_abs(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_abs()

    def convert_bool_cast(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_bool_cast()

    def convert_int_cast(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_int_cast()

    def convert_float_cast(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_float_cast()

    def convert_str_cast(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_str_cast()

    def convert_bytes_cast(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_bytes_cast()

    def convert_builtin(self, f, context, instance, a1=None):
        return instance.convert_masquerade_to_untyped().convert_builtin(f, a1)

    def convert_repr(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_repr()

    def convert_unary_op(self, context, instance, op):
        return instance.convert_masquerade_to_untyped().convert_unary_op(op)

    def _can_convert_to_type(self, otherType, explicit):
        return typeWrapper(self.interpreterTypeRepresentation)._can_convert_to_type(otherType, explicit)

    def _can_convert_from_type(self, otherType, explicit):
        return typeWrapper(self.interpreterTypeRepresentation)._can_convert_from_type(otherType, explicit)

    def convert_to_self_with_target(self, context, targetVal, sourceVal, explicit):
        assert False, "this should never be called"

    def convert_bin_op(self, context, l, op, r, inplace):
        return l.convert_masquerade_to_untyped().convert_bin_op(op, r, inplace)

    def convert_bin_op_reverse(self, context, r, op, l, inplace):
        return r.convert_masquerade_to_untyped().convert_bin_op_reverse(op, l, inplace)

    def convert_format(self, context, instance, formatSpecOrNone=None):
        return instance.convert_masquerade_to_untyped().convert_format(formatSpecOrNone)

    def convert_type_call(self, context, typeInst, args, kwargs):
        assert False, "this should never be called"

    def convert_call_on_container_expression(self, context, inst, argExpr):
        return inst.convert_masquerade_to_untyped().convert_call_on_container_expression(argExpr)

    def convert_type_call_on_container_expression(self, context, typeInst, argExpr):
        assert False, "this should never be called"

    def convert_method_call(self, context, instance, methodname, args, kwargs):
        return instance.convert_masquerade_to_untyped().convert_method_call(methodname, args, kwargs)

    def convert_context_manager_enter(self, context, instance):
        return instance.convert_masquerade_to_untyped().convert_context_manager_enter()

    def convert_context_manager_exit(self, context, instance, args):
        return instance.convert_masquerade_to_untyped().convert_context_manager_exit(args)
