#pragma once

#include "PyInstance.hpp"

class PyOneOfInstance : public PyInstance {
public:
    typedef OneOf modeled_type;

    static void copyConstructFromPythonInstanceConcrete(OneOf* oneOf, instance_ptr tgt, PyObject* pyRepresentation, bool isExplicit) {
        for (long k = 0; k < oneOf->getTypes().size(); k++) {
            Type* subtype = oneOf->getTypes()[k];

            if (pyValCouldBeOfType(subtype, pyRepresentation)) {
                try {
                    copyConstructFromPythonInstance(subtype, tgt+1, pyRepresentation);
                    *(uint8_t*)tgt = k;
                    return;
                } catch(PythonExceptionSet& e) {
                    PyErr_Clear();
                } catch(...) {
                }
            }
        }

        throw std::logic_error("Can't initialize a " + oneOf->name() + " from an instance of " +
            std::string(pyRepresentation->ob_type->tp_name));
        return;
    }

    static bool pyValCouldBeOfTypeConcrete(modeled_type* type, PyObject* pyRepresentation) {
        return true;
    }

    static PyObject* extractPythonObjectConcrete(modeled_type* oneofT, instance_ptr data) {
        std::pair<Type*, instance_ptr> child = oneofT->unwrap(data);
        return extractPythonObject(child.second, child.first);
    }
};
