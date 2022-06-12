import ctypes

import llvmlite.ir
from llvmlite import ir


class JitType:
    llvm = None

    def alloca(self, generator):
        raise NotImplementedError

    def slice(self):
        raise NotImplementedError


class Void(JitType):
    llvm = ir.VoidType()
    signed = None

    def to_ctype(self):
        return lambda x : None


class PrimitiveType(JitType):
    signed = None

    def __init__(self, size):
        self.size = size
        self.llvm = self.type(self.size)

    def __repr__(self):
        if self.signed:
            return f"Signed int of size {self.size}"
        else:
            return f"Unsigned int of size {self.size}"

    def alloca(self, generator):
        return generator.builder.alloca(self.llvm)


class BaseInt(PrimitiveType):
    type = ir.IntType

    int_ctypes = {
        True: {
            8: ctypes.c_int8,
            16: ctypes.c_int16,
            32: ctypes.c_int32,
            64: ctypes.c_int64
        },
        False: {
            1: ctypes.c_bool,  # should move this and create another class
            8: ctypes.c_uint8,
            16: ctypes.c_uint16,
            32: ctypes.c_uint32,
            64: ctypes.c_uint64
        }
    }

    def to_ctype(self):
        return self.int_ctypes[self.signed][self.size]

    def do_Add(self, generator, lhs, rhs):
        return generator.builder.add(lhs, rhs)

    def do_Sub(self, generator, lhs, rhs):
        return generator.builder.sub(lhs, rhs)

    def do_Mult(self, generator, lhs, rhs):
        return generator.builder.mul(lhs, rhs)

    def do_LShift(self, generator, lhs, rhs):
        return generator.builder.shl(lhs, rhs)

    def do_RShift(self, generator, lhs, rhs):
        return generator.builder.ashr(lhs, rhs)


class SignedInt(BaseInt):
    signed = True

    def do_Div(self, generator, lhs, rhs):
        return generator.builder.sdiv(lhs, rhs)

    def do_FloorDiv(self, generator, lhs, rhs):
        return generator.builder.sdiv(lhs, rhs)

    def do_USub(self, generator, lhs):
        return generator.builder.sub(ir.Constant(lhs.type, 0), lhs)

    def do_Mod(self, generator, lhs, rhs):
        result = generator.builder.urem(lhs, rhs)
        cmp = generator.builder.icmp_signed(">=", lhs, ir.Constant(lhs.type, 0))

        # if lhs < 0
        result2_1 = generator.builder.sub(ir.Constant(lhs.type, 0), lhs)
        result2_2 = generator.builder.urem(result2_1, rhs)
        result2_3 = generator.builder.sub(rhs, result2_2)
        result2 = generator.builder.urem(result2_3, rhs)

        return generator.builder.select(cmp, result, result2)

    def do_Eq(self, generator, lhs, rhs):
        return generator.builder.icmp_signed("==", lhs, rhs)

    def do_NotEq(self, generator, lhs, rhs):
        return generator.builder.icmp_signed("!=", lhs, rhs)

    def do_Gt(self, generator, lhs, rhs):
        return generator.builder.icmp_signed(">", lhs, rhs)

    def do_GtE(self, generator, lhs, rhs):
        return generator.builder.icmp_signed(">=", lhs, rhs)

    def do_Lt(self, generator, lhs, rhs):
        return generator.builder.icmp_signed("<", lhs, rhs)

    def do_LtE(self, generator, lhs, rhs):
        return generator.builder.icmp_signed("<=", lhs, rhs)

    def to_bool(self, generator, lhs):
        return generator.builder.icmp_signed("!=", lhs, ir.Constant(lhs.type, 0))


class UnsignedInt(BaseInt):
    signed = False

    def do_Div(self, generator, lhs, rhs):
        return generator.builder.udiv(lhs, rhs)

    def do_FloorDiv(self, generator, lhs, rhs):
        return generator.builder.udiv(lhs, rhs)

    def do_Mod(self, generator, lhs, rhs):
        return generator.builder.urem(lhs, rhs)

    def do_Eq(self, generator, lhs, rhs):
        return generator.builder.icmp_unsigned("==", lhs, rhs)

    def do_NotEq(self, generator, lhs, rhs):
        return generator.builder.icmp_unsigned("!=", lhs, rhs)

    def do_Gt(self, generator, lhs, rhs):
        return generator.builder.icmp_unsigned(">", lhs, rhs)

    def do_GtE(self, generator, lhs, rhs):
        return generator.builder.icmp_unsigned(">=", lhs, rhs)

    def do_Lt(self, generator, lhs, rhs):
        return generator.builder.icmp_unsigned("<", lhs, rhs)

    def do_LtE(self, generator, lhs, rhs):
        return generator.builder.icmp_unsigned("<=", lhs, rhs)

    def to_bool(self, generator, lhs):
        return generator.builder.icmp_unsigned("!=", lhs, ir.Constant(lhs.type, 0))


class BaseFloat(PrimitiveType):
    # signed = True

    def __init__(self):
        self.llvm = self.type()

    def __repr__(self):
        return f"Signed float of size {self.size}"

    def do_Add(self, generator, lhs, rhs):
        return generator.builder.fadd(lhs, rhs)

    def do_Sub(self, generator, lhs, rhs):
        return generator.builder.fsub(lhs, rhs)

    def do_USub(self, generator, lhs):
        lhs = generator.get_value(lhs)
        return generator.builder.fsub(ir.Constant(lhs.type, 0), lhs)

    def do_Div(self, generator, lhs, rhs):
        return generator.builder.fdiv(lhs, rhs)

    def do_Eq(self, generator, lhs, rhs):
        return generator.builder.fcmp_unordered("==", lhs, rhs)

    def do_NotEq(self, generator, lhs, rhs):
        return generator.builder.fcmp_unordered("!=", lhs, rhs)

    def do_Gt(self, generator, lhs, rhs):
        return generator.builder.fcmp_unordered(">", lhs, rhs)

    def do_GtE(self, generator, lhs, rhs):
        return generator.builder.fcmp_unordered(">=", lhs, rhs)

    def do_Lt(self, generator, lhs, rhs):
        return generator.builder.fcmp_unordered("<", lhs, rhs)

    def do_LtE(self, generator, lhs, rhs):
        return generator.builder.fcmp_unordered("<=", lhs, rhs)

    def to_bool(self, generator, lhs):
        return generator.builder.fcmp_unordered("!=", lhs, ir.Constant(lhs.type, 0))


class Float(BaseFloat):
    size = 32
    type = ir.FloatType

    def to_ctype(self):
        return ctypes.c_float


class Double(BaseFloat):
    size = 64
    type = ir.DoubleType

    def to_ctype(self):
        return ctypes.c_double


class ObjectType(JitType):
    pass


class StringType(ObjectType):
    def __init__(self, dimensions):
       self.type = i8
       self.size = dimensions
       self.llvm = ir.ArrayType(i8, dimensions)
       self._s_type = i8.to_ctype() * self.size

    def to_ctype(self):
        return self._s_type

    def __call__(self):
        new_str = String(self._s_type)
        return new_str

    def slice(self):
        return self.base_type


class String(StringType):
    def __init__(self, string_type):
        self._s_type = string_type
        self._string = self._s_type()

    def from_jtype(self, value):
        return self._string

    def __getitem__(self, item):
        return self._string[item]


class ArrayType(ObjectType):
    def __init__(self, base_type, dimensions):
        if len(dimensions) > 1:
            self.base_type = ArrayType(base_type, dimensions[1:])
            self.dimensions = dimensions[1:]
        else:
            self.base_type = base_type
            self.dimensions = dimensions

        self.size = dimensions[0]
        self.llvm = ir.ArrayType(self.base_type.llvm, dimensions[0])
        self._a_type = self.base_type.to_ctype() * self.size

    def to_ctype(self):
        return self._a_type

    def __call__(self):
        new_array = Array(self._a_type)
        return new_array

    def slice(self):
        return self.base_type


class Array(ArrayType):
    def __init__(self, array_type):
        self._a_type = array_type
        self._array = self._a_type()

    def from_jtype(self, value):
        return self._array

    def __getitem__(self, item):
        return self._array[item]

    def __setitem__(self, item, value):
        self._array[item] = value


def JArray(base_type, dimensions):
    if isinstance(dimensions, int):
        return ArrayType(base_type, [dimensions])
    return ArrayType(base_type, dimensions)


def JDict(key_type, dimension):
    if isinstance(dimension, int):
        return DictType(key_type, dimension)
    else:
        raise Exception("Dimension should be a fixed int")


def stringy(dimension):
    return StringType(dimension)


class PointerType(JitType):
    def __init__(self, pointee):
        self.pointee = pointee
        self.llvm = ir.PointerType(self.pointee.llvm)

    def from_jtype(self):
        return ctypes.POINTER(self.pointee.from_jtype())

    def to_ctype(self):
        return ctypes.POINTER(self.pointee.to_ctype())

    def alloca(self, generator):
        return generator.builder.alloca(self.llvm)


def pointer(pointee):
    return PointerType(pointee)


class ObjectPointer(PointerType):
    pass


def objectpointer(pointee):
    return ObjectPointer(pointee)


# helpers


def type_conversions(type_to_convert):
    if type_to_convert == int:
        return i64
    elif type_to_convert == float:
        return f64
    elif type_to_convert == bool:
        return bul
    elif isinstance(type_to_convert, StringType):
        return type_to_convert
#    elif isinstance(type_to_convert, DictType):
#        return type_to_convert
    elif isinstance(type_to_convert, ArrayType):
        return type_to_convert
    elif type_to_convert == str:
        return str
    return None


# instances of types

void = Void()

bul = UnsignedInt(1)  # should do a bool class ?

i8 = SignedInt(8)
u8 = UnsignedInt(8)

i16 = SignedInt(16)
u16 = UnsignedInt(16)

i32 = SignedInt(32)
u32 = UnsignedInt(32)

i64 = SignedInt(64)
u64 = UnsignedInt(64)

f32 = Float()
f64 = Double()

