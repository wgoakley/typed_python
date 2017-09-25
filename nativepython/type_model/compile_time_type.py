#   Copyright 2017 Braxton Mckee
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

import types
import nativepython
import nativepython.native_ast as native_ast

from nativepython.type_model.type_base import Type
from nativepython.type_model.typed_expression import TypedExpression
from nativepython.exceptions import ConversionException, UnassignableFieldException


class CompileTimeType(Type):
    @property
    def is_pod(self):
        return True
    
    @property
    def null_value(self):
        return native_ast.Constant.Struct(())

    def lower(self):
        return native_ast.Type.Struct(())

    @property
    def python_object_representation(self):
        raise ConversionException("Subclasses must implement")

    def as_typed_expression(self):
        return TypedExpression(
            native_ast.Expression.Constant(
                native_ast.Constant.Struct(())
                ),
            self
            )

    def convert_attribute(self, context, instance, attr):
        o = self.python_object_representation

        if not hasattr(o, attr):
            raise ConversionException("Can't get attribute %s from %s of type %s" % 
                    (attr,o, type(o)))

        return pythonObjectRepresentation(getattr(o, attr))


def representation_for(obj):
    def decorator(override):
        FreePythonObjectReference.free_python_object_overrides[obj] = override
        return override
    return decorator

class FreePythonObjectReference(CompileTimeType):
    free_python_object_overrides = {}

    def __init__(self, obj):
        object.__init__(self)
        self._original_obj = obj

        if obj in self.free_python_object_overrides:
            obj = self.free_python_object_overrides[obj]
        self._obj = obj

    @property
    def python_object_representation(self):
        return self._original_obj
        
    def convert_call(self, context, instance, args):
        if isinstance(self._obj, types.FunctionType):
            return context.call_py_function(self._obj, args)

        if self._obj is float:
            assert len(args) == 1
            return args[0].convert_to_type(nativepython.type_model.Float64)

        if self._obj is int:
            assert len(args) == 1
            return args[0].convert_to_type(nativepython.type_model.Int64)

        ClassType = nativepython.type_model.ClassType

        if ClassType.object_is_class(self._obj):
            return ClassType.convert_class_call(context, self._obj, args)

        if isinstance(self._obj, Type):
            if self._obj.is_ref:
                raise ConversionException("Can't instantiate %s" % self._obj)

            #we are initializing an element of the type
            for a in args:
                assert a.expr is not None

            tmp_ref = context.allocate_temporary(self._obj)

            return TypedExpression(
                self._obj.convert_initialize(context, tmp_ref, args).expr + 
                    context.activates_temporary(tmp_ref) + 
                    tmp_ref.expr,
                tmp_ref.expr_type
                )

        def to_py(x):
            if isinstance(x.expr_type.nonref_type, FreePythonObjectReference):
                return x.expr_type.nonref_type.python_object_representation

            if x.expr is not None and x.expr.matches.Constant:
                if x.expr.val.matches.Int or x.expr.val.matches.Float:
                    return x.expr.val.val
            return x

        call_args = [to_py(x) for x in args]
        try:
            py_call_result = self._obj(*call_args)
        except Exception as e:
            raise ConversionException("Failed to call %s with %s" % (self._obj, call_args))

        return pythonObjectRepresentation(py_call_result)

    def __repr__(self):
        return "FreePythonObject(%s)" % self._obj

def pythonObjectRepresentation(o):
    if isinstance(o,TypedExpression):
        return o

    if isinstance(o, bool):
        return TypedExpression(
            native_ast.Expression.Constant(
                native_ast.Constant.Int(val=1 if o else 0,bits=1,signed=False)
                ), 
            nativepython.type_model.Bool
            )

    if isinstance(o, int):
        return TypedExpression(
            native_ast.Expression.Constant(
                native_ast.Constant.Int(val=o,bits=64,signed=True)
                ), 
            nativepython.type_model.Int64
            )

    if isinstance(o, str):
        return TypedExpression(
            native_ast.Expression.Constant(
                native_ast.Constant.ByteArray(bytes(o))
                ), 
            nativepython.type_model.UInt8.pointer
            )

    if isinstance(o, float):
        return TypedExpression(
            native_ast.Expression.Constant(
                native_ast.Constant.Float(val=o,bits=64)
                ), 
            nativepython.type_model.Float64
            )

    if isinstance(o,CompileTimeType):
        return o.as_typed_expression()

    return FreePythonObjectReference(o).as_typed_expression()

class ExpressionFunction(CompileTimeType):
    def __init__(self, f):
        self.f = f

    def convert_call(self, context, instance, args):
        return self.f(context, args)

    def __repr__(self):
        return self.f.func_name

    @property
    def python_object_representation(self):
        return self

class TypeFunction(CompileTimeType):
    def __init__(self, f):
        self.f = f

    def convert_call(self, context, instance, args):
        def unwrap(x):
            if not isinstance(x, TypedExpression):
                raise ConversionException("Expected a TypedExpression, not %s" % x)
            t = x.expr_type
            if isinstance(t.nonref_type, FreePythonObjectReference):
                return t.nonref_type.python_object_representation
            else:
                return t

        def wrap(x):
            return pythonObjectRepresentation(x)

        unwrapped = [unwrap(x) for x in args]

        res = self.f(*unwrapped)
        
        return wrap(res)

    def __call__(self, *args):
        return self.f(*args)

    def __repr__(self):
        return self.f.func_name

    @property
    def python_object_representation(self):
        return self

class ExternalFunction(CompileTimeType):
    def __init__(self, name, output_type, input_types, implicit_type_casting,varargs,intrinsic):
        self.name = name
        self.output_type = output_type
        self.input_types = input_types
        self.implicit_type_casting = implicit_type_casting
        self.varargs = varargs
        self.intrinsic = intrinsic

    def convert_call(self, context, instance, args):
        if self.varargs:
            assert len(args) >= len(self.input_types)
        else:
            assert len(args) == len(self.input_types)

        args = [a.dereference() for a in args]

        if not self.implicit_type_casting:
            for i in xrange(len(input_types)):
                assert args[i].expr_type == self.input_types[i]
        else:
            args = list(args)
            for i in xrange(len(self.input_types)):
                if args[i].expr_type != self.input_types[i]:
                    args[i] = args[i].convert_to_type(self.input_types[i])

        return TypedExpression(
            native_ast.Expression.Call(
                target=native_ast.CallTarget(
                    name = self.name,
                    arg_types = [i.lower() for i in self.input_types],
                    output_type = self.output_type.lower(),
                    external=True,
                    varargs=self.varargs,
                    intrinsic=self.intrinsic
                    ),
                args=[a.expr for a in args]
                ),
            self.output_type
            )

    def __repr__(self):
        return self.name

    @classmethod
    def make(cls, name, output_type, input_types, implicit_type_casting=True,varargs=False,intrinsic=False):
        return ExternalFunction(name, output_type, input_types, implicit_type_casting,varargs,intrinsic)
