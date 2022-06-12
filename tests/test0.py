from tinyjit import tinyjit
import tinyjit.jit_types as t


# ================ array
arr = t.JArray(t.i64, 10)
x = arr()


@tinyjit
def array0(a: arr):
    a[1] = 100
    idk = a[1]
    return idk


@tinyjit
def mod(a: t.i64, b: t.i64):
    return a % b


@tinyjit
def call():
    return mod(15, 4)


@tinyjit
def test1():
    a = 1
    b = 1.7
    c = b + a + a + b
    return c


@tinyjit
def kinda_broken():
    a = "ggdafda"
    return a


@tinyjit
def test1111(a: t.i64, b: t.i64):
    a = a + b
    return a


@tinyjit
def for0():
    b = 0
    for a in range(2, 10, 2):
        b += a
    for c in range(12):
        b += c
    return b


@tinyjit
def for1():
    b = 0
    for a in range(2, 10):
        b += a
    return b


@tinyjit
def strings():
    var = "Hey"
    print(var)
    print(123)
    print("Hello")


@tinyjit
def add0(a: t.f64):
    return a + 2.123


@tinyjit
def and0():
    a = 1
    b = 2
    if a == 1 and b == 2:
        return True
    return False


@tinyjit
def mul0(a: t.i64, b: t.i64):
    return a * b


@tinyjit
def negation(a: t.i64):
    return -a


@tinyjit
def shift0(a: t.i64, b: t.i64):
    return a << b


@tinyjit
def coerce_bool(a: t.i64):
    if a:
        return True
    return False


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


@tinyjit
def void_none():
    return


@tinyjit
def aaa():
    return 1.1 + 2


@tinyjit
def bbb():
    a = aaa()
    return a


@tinyjit
def while0():
    c = 5
    d = 10
    while c:
        d += 1
        c = c - 1
        if c == 1:
            break
    return d


@tinyjit
def while1():
    a = 5
    b = 1
    while a != b:
        a -= 1
    return a


@tinyjit
def while_break1():
    a = 5
    while a:
        a -= 1
        if a == 3:
            break
    return a


@tinyjit
def for_break1():
    b = 1
    c = 5
    for a in range(3, 7):
        b *= a
        if a == c:
            break
    return b


@tinyjit
def print0(a: t.i64):
    print(a)


# @tinyjit
# def cast(a: t.i64, b: t.i32):
#     return a + b
#
# print(cast(3, 5))


