from llvmlite import ir

printf = None

def make(function_name):
    maker = globals().get(f"make_{function_name}", None)
    if not maker:
        return None
    return maker


def create_llvm(self, function_name, return_type=ir.VoidType, arguments=[], var_arg=False):
    mod: ir.Module = self.module
    function_pointer = mod.globals.get(function_name, None)
    if function_pointer:
        return function_pointer
    function_pointer = ir.Function(
        self.module,
        ir.FunctionType(return_type, arguments, var_arg=var_arg),
        function_name
    )
    return function_pointer


def make_print(self, args):
    from .generator import Value
    from . import jit_types as t

    global printf

    if isinstance(args[0].type, ir.ArrayType) or (hasattr(args[0], 'type') and args[0].type == str):
        if isinstance(args[0].type, ir.ArrayType):
            old_str = args[0].constant.decode("utf8")
            old_str += "\n\0"
            s_const = ir.Constant(ir.ArrayType(ir.IntType(8), len(old_str)), bytearray(old_str.encode("utf8")))
            global_str = ir.GlobalVariable(self.module, s_const.type, name=f"str_{self.help_cont}")
            self.help_cont += 1
            global_str.linkage = 'internal'
            global_str.global_constant = True
            global_str.initializer = s_const
        else:
            global_str = args[0].llvm

        str_bit = self.builder.bitcast(global_str, ir.IntType(8).as_pointer())

        if not printf:
            print_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg=True)
            printf = ir.Function(self.module, print_ty, name="printf")

        result = self.builder.call(printf, [str_bit])
    else:
        if isinstance(args[0].type, ir.IntType):
            current_ty = ir.IntType(64)
        else:
            current_ty = ir.DoubleType()

        if not printf:
            printf = create_llvm(
                self,
                "printf",
                ir.IntType(64),
                [ir.PointerType(ir.IntType(8)), current_ty],
                var_arg=True,
            )
        s1 = ir.GlobalVariable(self.module, ir.ArrayType(ir.IntType(8), 6), f"str_{self.help_cont}")
        self.help_cont += 1
        s1.initializer = ir.Constant(ir.ArrayType(ir.IntType(8), 6), bytearray("%lld\n\x00", encoding="utf8"))
        s2 = self.builder.gep(s1, [self.zero, self.zero])

        result = self.builder.call(printf, [s2] + args)

    return Value(t.u64, result, None)



