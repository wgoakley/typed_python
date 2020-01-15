#include "PyInstance.hpp"
#include "FunctionType.hpp"

/* static */
PyObject* Function::Overload::buildFunctionObj(instance_ptr self) const {
    if (mCachedFunctionObj) {
        return incref(mCachedFunctionObj);
    }

    PyObject* res = PyFunction_New(mFunctionCode, mFunctionGlobals);

    if (!res) {
        throw PythonExceptionSet();
    }

    if (mFunctionDefaults) {
        if (PyFunction_SetDefaults(res, mFunctionDefaults) == -1) {
            throw PythonExceptionSet();
        }
    }

    if (mFunctionAnnotations) {
        if (PyFunction_SetAnnotations(res, mFunctionAnnotations) == -1) {
            throw PythonExceptionSet();
        }
    }

    int closureVarCount = PyCode_GetNumFree((PyCodeObject*)mFunctionCode);

    if (mFunctionClosureVarnames.size() != closureVarCount) {
        throw std::runtime_error("Invalid closure: wrong number of cells.");
    }

    if (closureVarCount) {
        // for the moment, assume 'globals in cells' is all-or-nothing.
        if (mFunctionGlobalsInCells.size()) {
            if (mFunctionGlobalsInCells.size() != closureVarCount) {
                throw std::runtime_error("Invalid closure: wrong number of cells.");
            }

            PyObjectStealer closureTup(PyTuple_New(closureVarCount));

            for (long k = 0; k < closureVarCount; k++) {
                PyTuple_SetItem(
                    (PyObject*)closureTup,
                    k,
                    incref(mFunctionGlobalsInCells.find(mFunctionClosureVarnames[k])->second)
                );
            }

            if (PyFunction_SetClosure(res, (PyObject*)closureTup) == -1) {
                throw PythonExceptionSet();
            }

        } else {
            if (mClosureType->bytecount() != 0) {
                if (self == nullptr) {
                    throw std::runtime_error("Expected a populated closure");
                }
            }

            if (closureVarCount != mClosureType->getTypes().size()) {
                throw std::runtime_error("Invalid closure: wrong number of cells.");
            }

            PyObjectStealer closureTup(PyTuple_New(closureVarCount));

            for (long k = 0; k < closureVarCount; k++) {
                try {
                    if (mClosureType->getTypes()[k]->getTypeCategory() == Type::TypeCategory::catPyCell) {
                        // we're actually storing the PyCellObject in our closure directly
                        PyTuple_SetItem(
                            (PyObject*)closureTup,
                            k,
                            ((PyCellType*)mClosureType->getTypes()[k])->getPyObj(
                                self + mClosureType->getOffsets()[k]
                            )
                        );
                    } else
                    if (mClosureType->getTypes()[k]->getTypeCategory() == Type::TypeCategory::catTypedCell) {
                        // we're actually storing this as a typed cell in our closure directly.
                        // we don't know how to mirror this down into interpreter code.
                        // we should be ensuring that we never call this method and instead dispatch
                        // to compiled code at all times. Alternatively, we could rewrite the opcodes
                        // to handle typed closures.

                        // for now, we just throw an exception
                        throw std::runtime_error("Invalid closure: typed closure encountered");
                    } else {
                        PyObjectStealer asPyObj(
                            PyInstance::extractPythonObject(
                                self + mClosureType->getOffsets()[k],
                                mClosureType->getTypes()[k]
                            )
                        );

                        if (!asPyObj) {
                            throw PythonExceptionSet();
                        }

                        PyTuple_SetItem((PyObject*)closureTup, k, PyCell_New(asPyObj));
                    }
                } catch(...) {
                    // make sure the tuple is populated before ripping it down
                    for (long j = k; j < closureVarCount; j++) {
                        PyTuple_SetItem((PyObject*)closureTup, j, incref(Py_None));
                    }
                    throw;
                }
            }

            if (PyFunction_SetClosure(res, (PyObject*)closureTup) == -1) {
                throw PythonExceptionSet();
            }
        }
    }

    if (mClosureType->bytecount() == 0) {
        mCachedFunctionObj = incref(res);
    }

    return res;
}
