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

    if (closureVarCount) {
        if (mClosureType->bytecount() != 0) {
            if (self == nullptr) {
                throw std::runtime_error("Expected a populated closure");
            }
        }

        PyObjectStealer closureTup(PyTuple_New(closureVarCount));

        if (closureVarCount != mClosureType->getTypes().size()) {
            throw std::runtime_error("Invalid closure: wrong number of cells.");
        }

        for (long k = 0; k < closureVarCount; k++) {
            try {
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

    if (mClosureType->bytecount() == 0) {
        mCachedFunctionObj = incref(res);
    }

    return res;
}
