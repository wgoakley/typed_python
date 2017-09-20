import nativepython.util as util

addr = util.addr

@util.typefun
def Vector(T):
    class Vector:
        def __init__(self):
            self._ptr = T.pointer(0)
            self._reserved = 0
            self._size = 0

        def __destructor__(self):
            self._teardown()

        def __assign__(self, other):
            self._teardown()
            self._become(util.ref(other))

        def __copy_constructor__(self, other):
            self._become(util.ref(other))

        def _become(self, other):
            if other._ptr:
                self._ptr = T.pointer(util.malloc(T.sizeof * other._reserved))
                self._reserved = other._reserved
                self._size = other._size

                for i in xrange(self._size):
                    util.in_place_new(self._ptr + i, other._ptr[i])
            else:
                self._ptr = T.pointer(0)
                self._reserved = 0
                self._size = 0
            
        def _teardown(self):
            if self._ptr:
                for i in xrange(self._size):
                    util.in_place_destroy(self._ptr + i)

                util.free(self._ptr)

        def __len__(self):
            return self._size
            
        def __getitem__(self, index):
            return util.ref(self._ptr[index])

        def __setitem__(self, index, value):
            self._ptr[index] = value

        def append(self, value):
            if self._reserved <= self._size:
                self.reserve(self._size * 2 + 1)

            util.in_place_new(self._ptr + self._size, value)

            self._size += 1

        def reserve(self, count):
            if count < self._size:
                count = self._size

            if count == self._reserved:
                return

            new_ptr = T.pointer(util.malloc(T.sizeof * count))

            for i in xrange(self._size):
                util.in_place_new(new_ptr + i, self._ptr[i])
                util.in_place_destroy(self._ptr + i)

            if self._ptr:
                util.free(self._ptr)

            self._ptr = new_ptr
            self._reserved = count
    
    return Vector



