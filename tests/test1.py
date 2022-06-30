from tinyjit import tinyjit
import tinyjit.jit_types as t


arr = t.JArray(t.i64, 10)
x = arr()


@tinyjit
def array0(a: arr):
    for i in range(10):
        a[i] = i

    for i in range(10):
        print(a[i])


print("====== Array function ======")
array0(x)
