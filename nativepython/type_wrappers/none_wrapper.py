#   Coyright 2017-2019 Nativepython Authors
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

from nativepython.type_wrappers.wrapper import Wrapper
from typed_python import NoneType, Int32
import nativepython.native_ast as native_ast


class NoneWrapper(Wrapper):
    is_pod = True
    is_empty = True
    is_pass_by_ref = False

    def __init__(self):
        super().__init__(NoneType)

    def convert_default_initialize(self, context, target):
        pass

    def getNativeLayoutType(self):
        return native_ast.Type.Void()

    def convert_assign(self, context, target, toStore):
        pass

    def convert_copy_initialize(self, context, target, toStore):
        pass

    def convert_destroy(self, context, instance):
        pass

    def convert_hash(self, context, expr):
        return context.constant(Int32(0))

    def convert_bin_op(self, context, left, op, right):
        if right.expr_type == self:
            if op.matches.Eq:
                return context.constant(True)
            if op.matches.NotEq or op.matches.Lt or op.matches.LtE or op.matches.Gt or op.matches.GtE:
                return context.constant(False)
            if op.matches.Is:
                return context.constant(True)
            if op.matches.IsNot:
                return context.constant(False)

        return super().convert_bin_op(context, left, op, right)
