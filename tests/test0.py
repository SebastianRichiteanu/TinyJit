from tinyjit import tinyjit
import tinyjit.jit_types as t


# ================ array
arr = t.JArray(t.i64, 10)
x = arr()


@tinyjit
def array0(a: arr):

    for i in range(10):
        a[i] = i

    for i in range(10):
        print(a[i])

#print("====== Array function ======")
#array0(x)


@tinyjit
def mod(a: t.i64, b: t.i64):
    return a % b

# print("====== Mod function ======")
# print(mod(21, 4))


@tinyjit
def call():
    b = mod(21, 4)
    return b


print("====== Call function ======")
mod(21, 4)
print(call())


@tinyjit
def int_float():
    a = 1
    b = 1.7
    c = b + a + a + b
    return c


# print("====== int_float function ======")
# print(int_float())


@tinyjit
def change_value(a: t.i64, b: t.i64):
    a = a + b
    return a


# print("====== change_value function ======")
# print(change_value(5, 7))


@tinyjit
def for0():
    b = 0
    for a in range(2, 10, 2):  # 2 + 4 + 6 + 8 = 20
        b += a
    for c in range(12):  # 1 + 2 + .. + 11 = 66
        b += c
    return b


# print("====== for function ======")
# print(for0())


@tinyjit
def for_break():
    b = 1
    c = 5
    for a in range(3, 7):
        b *= a  # 1 * 3 = 3 * 4 = 12 * 5 = 60
        if a == c:
            break
    return b


# print("====== for_break function ======")
# print(for_break())


@tinyjit
def strings():
    var = "Hey"
    print(var)
    print(123)
    print("Hello")


# print("====== strings function ======")
# strings()


@tinyjit
def fadd(a: t.f64):
    return a + 2.123


# print("====== fadd function ======")
# print(fadd(3.14))


@tinyjit
def and0():
    a = 1
    b = 2
    if a == 1 and b == 2:
        return True
    return False


# print("====== and0 function ======")
# print(and0())


@tinyjit
def negation(a: t.i64):
    return -a


# print("====== negation function ======")
# print(negation(3))


@tinyjit
def shift0(a: t.i64, b: t.i64):
    return a << b


# print("====== shift0 function ======")
# print(shift0(8, 2))


@tinyjit
def coerce_bool(a: t.i64):
    if a:
        return True
    return False


# print("====== coerce_bool function ======")
# print(coerce_bool(3))


@tinyjit
def cond(a: t.i64, b: t.i64, c: t.i8):
    # ==, !=, >, >=, <, <=
    if c == 0:
        return a == b
    elif c == 1:
        return a != b
    elif c == 2:
        return a > b
    elif c == 3:
        return a >= b
    elif c == 4:
        return a < b
    elif c == 5:
        return a <= b
    return False


# print("====== cond function ======")
# print(cond(5, 4, 5))


@tinyjit
def void_none():
    return


# print("====== void_none function ======")
# print(void_none())


@tinyjit
def while0():
    a = 5
    b = 2
    while a != b:
        a -= 1
    return a


# print("====== while0 function ======")
# print(while0())


@tinyjit
def while_break():
    c = 5
    d = 10
    while c:
        d += c  # 10 + 5 = 15 + 4 = 19 + 3 = 22
        c = c - 1
        if c == 2:
            break
    return d


# print("====== while_break function ======")
# print(while_break())

