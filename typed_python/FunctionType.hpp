/******************************************************************************
   Copyright 2017-2019 typed_python Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
******************************************************************************/

#pragma once

#include "Type.hpp"
#include "ReprAccumulator.hpp"
#include "Format.hpp"

class Function : public Type {
public:
    class FunctionArg {
    public:
        FunctionArg(std::string name, Type* typeFilterOrNull, PyObject* defaultValue, bool isStarArg, bool isKwarg) :
            m_name(name),
            m_typeFilter(typeFilterOrNull),
            m_defaultValue(defaultValue),
            m_isStarArg(isStarArg),
            m_isKwarg(isKwarg)
        {
            assert(!(isStarArg && isKwarg));
        }

        std::string getName() const {
            return m_name;
        }

        PyObject* getDefaultValue() const {
            return m_defaultValue;
        }

        Type* getTypeFilter() const {
            return m_typeFilter;
        }

        bool getIsStarArg() const {
            return m_isStarArg;
        }

        bool getIsKwarg() const {
            return m_isKwarg;
        }

        bool getIsNormalArg() const {
            return !m_isKwarg && !m_isStarArg;
        }

        template<class visitor_type>
        void _visitReferencedTypes(const visitor_type& visitor) {
            if (m_typeFilter) {
                visitor(m_typeFilter);
            }
        }

        bool operator<(const FunctionArg& other) const {
            if (m_name < other.m_name) {
                return true;
            }
            if (m_name > other.m_name) {
                return false;
            }
            if (m_typeFilter < other.m_typeFilter) {
                return true;
            }
            if (m_typeFilter > other.m_typeFilter) {
                return false;
            }
            if (m_defaultValue < other.m_defaultValue) {
                return true;
            }
            if (m_defaultValue > other.m_defaultValue) {
                return false;
            }
            if (m_isStarArg < other.m_isStarArg) {
                return true;
            }
            if (m_isStarArg > other.m_isStarArg) {
                return false;
            }
            if (m_isKwarg < other.m_isKwarg) {
                return true;
            }
            if (m_isKwarg > other.m_isKwarg) {
                return false;
            }

            return false;
        }

    private:
        std::string m_name;
        Type* m_typeFilter;
        PyObject* m_defaultValue;
        bool m_isStarArg;
        bool m_isKwarg;
    };

    class CompiledSpecialization {
    public:
        CompiledSpecialization(
                    compiled_code_entrypoint funcPtr,
                    Type* returnType,
                    const std::vector<Type*>& argTypes
                    ) :
            mFuncPtr(funcPtr),
            mReturnType(returnType),
            mArgTypes(argTypes)
        {}

        compiled_code_entrypoint getFuncPtr() const {
            return mFuncPtr;
        }

        Type* getReturnType() const {
            return mReturnType;
        }

        const std::vector<Type*>& getArgTypes() const {
            return mArgTypes;
        }

    private:
        compiled_code_entrypoint mFuncPtr;
        Type* mReturnType;
        std::vector<Type*> mArgTypes;
    };

    class Overload {
    public:
        Overload(
            PyObject* pyFuncCode,
            PyObject* pyFuncGlobals,
            PyObject* pyFuncDefaults,
            PyObject* pyFuncAnnotations,
            NamedTuple* closureType,
            Type* returnType,
            const std::vector<FunctionArg>& args
            ) :
                mFunctionCode(incref(pyFuncCode)),
                mFunctionGlobals(incref(pyFuncGlobals)),
                mFunctionDefaults(incref(pyFuncDefaults)),
                mFunctionAnnotations(incref(pyFuncAnnotations)),
                mReturnType(returnType),
                mArgs(args),
                mCompiledCodePtr(nullptr),
                mHasKwarg(false),
                mHasStarArg(false),
                mMinPositionalArgs(0),
                mMaxPositionalArgs(-1),
                mClosureType(closureType),
                mCachedFunctionObj(nullptr)
        {
            long argsWithDefaults = 0;
            long argsDefinitelyConsuming = 0;

            for (auto arg: mArgs) {
                if (arg.getIsStarArg()) {
                    mHasStarArg = true;
                }
                else if (arg.getIsKwarg()) {
                    mHasKwarg = true;
                }
                else if (arg.getDefaultValue()) {
                    argsWithDefaults++;
                } else {
                    argsDefinitelyConsuming++;
                }
            }

            mMinPositionalArgs = argsDefinitelyConsuming;
            if (!mHasStarArg) {
                mMaxPositionalArgs = argsDefinitelyConsuming + argsWithDefaults;
            }
        }

        std::string toString() const {
            std::ostringstream str;

            str << "(";

            for (long k = 0; k < mArgs.size(); k++) {
                if (k) {
                    str << ", ";
                }

                if (mArgs[k].getIsStarArg()) {
                    str << "*";
                }

                if (mArgs[k].getIsKwarg()) {
                    str << "**";
                }

                str << mArgs[k].getName();

                if (mArgs[k].getDefaultValue()) {
                    str << "=...";
                }

                if (mArgs[k].getTypeFilter()) {
                    str << ": " << mArgs[k].getTypeFilter()->name();
                }
            }

            str << ")";

            if (mReturnType) {
                str << " -> " << mReturnType->name();
            }

            return str.str();
        }

        // return the FunctionArg* that a positional argument would map to, or 'nullptr' if
        // it wouldn't
        const FunctionArg* argForPositionalArgument(long argIx) const {
            if (argIx >= mArgs.size()) {
                return nullptr;
            }

            if (mArgs[argIx].getIsStarArg() || mArgs[argIx].getIsKwarg()) {
                return nullptr;
            }

            return &mArgs[argIx];
        }

        // can we possibly match 'argCount' positional arguments?
        bool couldMatchPositionalCount(long argCount) const {
            return argCount >= mMinPositionalArgs && argCount < mMaxPositionalArgs;
        }

        bool disjointFrom(const Overload& other) const {
            // we need to determine if all possible call signatures of these overloads
            // would route to one or the other unambiguously. we ignore keyword callsignatures
            // for the moment. For each possible positional argument, if we get disjointedness
            // then the whole set is disjoint.

            // if the set of numbers of arguments we can accept are disjoint, then we can't possibly
            // match the same queries.
            if (mMaxPositionalArgs < other.mMinPositionalArgs || other.mMaxPositionalArgs < mMinPositionalArgs) {
                return true;
            }

            // now check each positional argument
            for (long k = 0; k < mArgs.size() && k < other.mArgs.size(); k++) {
                const FunctionArg* arg1 = argForPositionalArgument(k);
                const FunctionArg* arg2 = other.argForPositionalArgument(k);

                if (arg1 && arg2 && !arg1->getDefaultValue() && !arg2->getDefaultValue() && arg1->getTypeFilter() && arg2->getTypeFilter()) {
                    if (arg1->getTypeFilter()->canConstructFrom(arg2->getTypeFilter(), false) == Maybe::False) {
                        return true;
                    }
                }
            }

            return false;
        }

        Type* getReturnType() const {
            return mReturnType;
        }

        const std::vector<FunctionArg>& getArgs() const {
            return mArgs;
        }

        template<class visitor_type>
        void _visitReferencedTypes(const visitor_type& visitor) {
            if (mReturnType) {
                visitor(mReturnType);
            }
            for (auto& a: mArgs) {
                a._visitReferencedTypes(visitor);
            }
        }

        template<class visitor_type>
        void _visitContainedTypes(const visitor_type& visitor) {
            visitor(mClosureType);
        }

        const std::vector<CompiledSpecialization>& getCompiledSpecializations() const {
            return mCompiledSpecializations;
        }

        void addCompiledSpecialization(compiled_code_entrypoint e, Type* returnType, const std::vector<Type*>& argTypes) {
            mCompiledSpecializations.push_back(CompiledSpecialization(e,returnType,argTypes));
        }

        void touchCompiledSpecializations() {
            //force the memory for the compiled specializations to move.
            std::vector<CompiledSpecialization> other = mCompiledSpecializations;
            std::swap(mCompiledSpecializations, other);
        }

        bool operator<(const Overload& other) const {
            if (mFunctionCode < other.mFunctionCode) { return true; }
            if (mFunctionCode > other.mFunctionCode) { return false; }

            if (mFunctionGlobals < other.mFunctionGlobals) { return true; }
            if (mFunctionGlobals > other.mFunctionGlobals) { return false; }

            if (mClosureType < other.mClosureType) { return true; }
            if (mClosureType > other.mClosureType) { return false; }

            if (mReturnType < other.mReturnType) { return true; }
            if (mReturnType > other.mReturnType) { return false; }

            if (mArgs < other.mArgs) { return true; }
            if (mArgs > other.mArgs) { return false; }

            return false;
        }

        NamedTuple* getClosureType() const {
            return mClosureType;
        }

        PyObject* getFunctionCode() const {
            return mFunctionCode;
        }

        PyObject* getFunctionGlobals() const {
            return mFunctionGlobals;
        }

        // create a new function object for this closure (or cache it
        // if we have no closure)
        PyObject* buildFunctionObj(instance_ptr self) const;

    private:
        PyObject* mFunctionCode;

        PyObject* mFunctionGlobals;

        PyObject* mFunctionDefaults;

        PyObject* mFunctionAnnotations;

        mutable PyObject* mCachedFunctionObj;

        // the type of the function's closure. each local (e.g. non-global-scope variable)
        // is represented here by name.
        NamedTuple* mClosureType;

        Type* mReturnType;

        std::vector<FunctionArg> mArgs;

        // in compiled code, the closure arguments get passed in front of the
        // actual function arguments
        std::vector<CompiledSpecialization> mCompiledSpecializations;

        compiled_code_entrypoint mCompiledCodePtr; //accepts a pointer to packed arguments and another pointer with the return value

        bool mHasStarArg;
        bool mHasKwarg;
        size_t mMinPositionalArgs;
        size_t mMaxPositionalArgs;
    };

    Function(std::string inName,
            const std::vector<Overload>& overloads,
            bool isEntrypoint
            ) :
        Type(catFunction),
        mOverloads(overloads),
        mIsEntrypoint(isEntrypoint)
    {
        m_name = inName;

        m_is_simple = false;

        std::vector<Type*> overloadTypes;

        for (auto& o: mOverloads) {
            overloadTypes.push_back(o.getClosureType());
        }

        mClosureType = Tuple::Make(overloadTypes);

        m_size = mClosureType->bytecount();
        m_is_default_constructible = m_size == 0;

        endOfConstructorInitialization(); // finish initializing the type object.
    }

    static Function* Make(std::string inName, std::vector<Overload>& overloads, bool isEntrypoint) {
        static std::mutex guard;

        std::lock_guard<std::mutex> lock(guard);

        typedef std::tuple<const std::string, const std::vector<Overload>, bool> keytype;

        static std::map<keytype, Function*> m;

        auto it = m.find(keytype(inName, overloads, isEntrypoint));
        if (it == m.end()) {
            it = m.insert(std::pair<keytype, Function*>(
                keytype(inName, overloads, isEntrypoint),
                new Function(inName, overloads, isEntrypoint)
            )).first;
        }

        return it->second;
    }

    template<class visitor_type>
    void _visitContainedTypes(const visitor_type& visitor) {
        for (auto& o: mOverloads) {
            o._visitContainedTypes(visitor);
        }
        visitor(mClosureType);
    }

    template<class visitor_type>
    void _visitReferencedTypes(const visitor_type& visitor) {
        for (auto& o: mOverloads) {
            o._visitReferencedTypes(visitor);
        }
    }

    static Function* merge(Function* f1, Function* f2) {
        std::vector<Overload> overloads(f1->mOverloads);
        for (auto o: f2->mOverloads) {
            overloads.push_back(o);
        }

        return Function::Make(f1->m_name, overloads, f1->isEntrypoint() || f2->isEntrypoint());
    }

    bool cmp(instance_ptr left, instance_ptr right, int pyComparisonOp, bool suppressExceptions) {
        return mClosureType->cmp(left, right, pyComparisonOp, suppressExceptions);
    }

    template<class buf_t>
    void deserialize(instance_ptr self, buf_t& buffer, size_t wireType) {
        assertWireTypesEqual(wireType, WireType::EMPTY);
    }

    template<class buf_t>
    void serialize(instance_ptr self, buf_t& buffer, size_t fieldNumber) {
        buffer.writeEmpty(fieldNumber);
    }

    void repr(instance_ptr self, ReprAccumulator& stream, bool isRepr) {
        stream << "<function " << m_name << ">";
    }

    typed_python_hash_type hash(instance_ptr left) {
        if (mClosureType->bytecount() == 0) {
            return 1;
        }

        return mClosureType->hash(left);
    }

    void constructor(instance_ptr self) {
        if (mClosureType->bytecount() == 0) {
            return;
        }

        mClosureType->constructor(self);
    }

    void destroy(instance_ptr self) {
        if (mClosureType->bytecount() == 0) {
            return;
        }

        mClosureType->destroy(self);
    }

    void copy_constructor(instance_ptr self, instance_ptr other) {
        if (mClosureType->bytecount() == 0) {
            return;
        }

        mClosureType->copy_constructor(self, other);
    }

    void assign(instance_ptr self, instance_ptr other) {
        if (mClosureType->bytecount() == 0) {
            return;
        }

        mClosureType->assign(self, other);
    }

    const std::vector<Overload>& getOverloads() const {
        return mOverloads;
    }

    void addCompiledSpecialization(
                    long whichOverload,
                    compiled_code_entrypoint entrypoint,
                    Type* returnType,
                    const std::vector<Type*>& argTypes
                    ) {
        if (whichOverload < 0 || whichOverload >= mOverloads.size()) {
            throw std::runtime_error("Invalid overload index.");
        }

        mOverloads[whichOverload].addCompiledSpecialization(entrypoint, returnType, argTypes);
    }

    // a test function to force the compiled specialization table to change memory
    // position
    void touchCompiledSpecializations(long whichOverload) {
        if (whichOverload < 0 || whichOverload >= mOverloads.size()) {
            throw std::runtime_error("Invalid overload index.");
        }

        mOverloads[whichOverload].touchCompiledSpecializations();
    }

    bool isEntrypoint() const {
        return mIsEntrypoint;
    }

    Function* withEntrypoint(bool isEntrypoint) {
        return Function::Make(name(), mOverloads, isEntrypoint);
    }

    Tuple* getClosureType() const {
        return mClosureType;
    }

private:
    std::vector<Overload> mOverloads;

    // tuple of named tuples, one per overload, containing the
    // bound local variables for that overload.
    Tuple* mClosureType;

    bool mIsEntrypoint;
};
