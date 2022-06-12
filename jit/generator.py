import ast
import inspect
import sys

import llvmlite.ir
from llvmlite import binding
from typing import Union

from . import standard_func
from .jit_types import *


class JitObj:
    def __init__(self, type, llvm, obj):
        self.type = type
        self.llvm = llvm
        self.obj = obj


class Value(JitObj):
    pass


class Variable(JitObj):
    pass


class TypeTarget:
    def __init__(self, type_target_list, type_target):
        self.type_target_list = type_target_list
        self.type_target_list.append(type_target)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.type_target_list.pop()


class JitGenerator:
    def __init__(self):
        self.modules = {}
        self.target_data = None

    def get_value(self, obj):
        if isinstance(obj, Value):
            return obj.llvm
        elif isinstance(obj, Variable):
            return self.builder.load(obj.llvm)
        elif isinstance(obj, llvmlite.ir.CallInstr) or isinstance(obj, llvmlite.ir.CastInstr):
            return obj
        else:
            raise Exception(f"Can't get value of {obj}. It is NOT an instance of Value or Variable")

    def get_annotation(self, annotation):
        item = ast.unparse(annotation)
        argument_type = eval(item, self.python_mod.__dict__)
        if not argument_type:
            raise Exception("Annotation not found!")

        if not isinstance(argument_type, PrimitiveType):
            converted_type = type_conversions(argument_type)
            if not converted_type:
                raise Exception(f"Type {argument_type} is not supported!")
            argument_type = converted_type

        if isinstance(argument_type, ObjectType):
            argument_type = objectpointer(argument_type)

        return argument_type

    def to_bool(self, expression, node):
        if node.type != bul:  # should change when i create bool class
            expression = node.type.to_bool(self, expression)
        return expression

    def generate_function_name(self, name):
        return f"tinyjit.{name}"

    def generate(self, instruction):
        instruction_type = instruction.__class__.__name__

        visit = getattr(self, f"visit_{instruction_type}", None)
        if not visit:
            raise Exception(f"Couldn't find visit_{instruction_type}")

        try:
            return visit(instruction)
        except BaseException as e:
            raise e

    def generate_all(self, obj, aa):
        # string name of the module this function lives in
        self.help_cont = 0
        self.aa = aa
        self.python_mod_name: str = obj.__module__
        # reference to module object that hosts this function
        self.python_mod = sys.modules.get(self.python_mod_name)
        self.module: ir.Module = self.modules.get(self.python_mod_name)  # try to get from modules dictionary

        if not self.module:  # if it doesn't exist in modules, create and add it
            self.module = ir.Module(self.python_mod_name)
            self.modules[self.python_mod_name] = self.module

        if not self.target_data:
            self.target_data = binding.create_target_data(self.module.data_layout)
            self.bitness = (ir.PointerType(ir.IntType(8)).get_abi_size(self.target_data) * 8)
            self.mem = ir.IntType(self.bitness)
            self.mem_ptr = ir.PointerType(self.mem)
            self.mem_val = lambda val: ir.Constant(ir.IntType(self.bitness), val)
            self.zero = self.mem_val(0)

        self.debug_var = True
        self.obj = obj
        self.instructions = ast.parse(inspect.getsource(obj))
        self.var_counter = 0

        if self.debug_var:
            print(inspect.getsource(obj))
            print(self.instructions)

            with open("../debug/ast.txt", "w") as f:
                f.write(ast.dump(ast.parse(self.instructions), indent=5))

            self.generate(self.instructions)

            with open("../debug/debug.llvm", "w") as f:
                f.write(str(self.module))

    def type_target(self, type_target):
        return TypeTarget(self.type_targets, type_target)

    def test_no_class(self, type1, type2):
        if isinstance(type1, SignedInt) and isinstance(type2, ir.IntType):
            return False
        if isinstance(type1, ir.IntType) and isinstance(type2, SignedInt):
            return False
        if isinstance(type1, UnsignedInt) and isinstance(type2, ir.IntType):
            return False
        if isinstance(type1, ir.IntType) and isinstance(type2, UnsignedInt):
            return False
        if isinstance(type1, Float) and isinstance(type2, ir.FloatType):
            return False
        if isinstance(type1, ir.FloatType) and isinstance(type2, Float):
            return False
        if isinstance(type1, Double) and isinstance(type2, ir.DoubleType):
            return False
        if isinstance(type1, ir.DoubleType) and isinstance(type2, Double):
            return False
        return True


    def visit_Module(self, node: ast.Module):
        for module in node.body:
            self.generate(module)

    def visit_classDef(self, node: ast.ClassDef):
        raise NotImplementedError

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.type_targets = []
        self.break_stack = []
        self.loop_stack = []
        self.arg_types = []
        self.type_data = {}
        self.variables = {}
        self.type_unset = False

        for argument in node.args.args:
            if not argument.annotation:
                raise Exception(f"Argument {argument.arg} not annoted")
            argument_type = self.get_annotation(argument.annotation)
            self.arg_types.append(argument_type)


        self.return_type: PrimitiveType = self.type_data.get("return", None)

        if not self.return_type:
            self.type_unset = True
            self.return_type = void

        function_return_type = (ir.VoidType() if self.return_type is void else self.return_type)

        self.function_type = ir.FunctionType(function_return_type, [arg.llvm for arg in self.arg_types], False)
        self.function = ir.Function(self.module, self.function_type, node.name)
        self.function.return_type = self.return_type
        self.setup_block = self.function.append_basic_block("setup")
        self.entry_block = self.function.append_basic_block("entry")
        self.exit_block = self.function.append_basic_block("exit")
        self.builder = ir.IRBuilder(self.setup_block)

        if self.return_type is not void:
            self.return_value = Variable(self.return_type, self.return_type.alloca(self), None)
        else:
            self.return_value = void

        idx = 0
        for function_arg, arg, arg_type in zip(self.function.args, node.args.args, self.arg_types):
            value = Value(arg_type, function_arg, arg)
            if not isinstance(value.type, ObjectPointer):
                var = self.create_name(ast.Name(value.obj.arg), value)
                self.variables[arg.arg] = var
                try:
                    if arg_type is None:
                        if type(self.aa[idx]) == int:
                            self.builder.store(ir.Constant(ir.IntType(64), self.aa[idx]), var.llvm)
                        else:
                            self.builder.store(ir.Constant(ir.DoubleType(), self.aa[idx]), var.llvm)
                    else:
                        if isinstance(arg_type, SignedInt) or isinstance(arg_type, UnsignedInt):
                            self.builder.store(ir.Constant(ir.IntType(arg_type.size), self.aa[idx]), var.llvm)
                        elif isinstance(arg_type, Float):
                            self.builder.store(ir.Constant(ir.FloatType(), self.aa[idx]), var.llvm)
                        elif isinstance(arg_type, Double):
                            self.builder.store(ir.Constant(ir.DoubleType(), self.aa[idx]), var.llvm)
                except IndexError:
                    raise Exception(f"Arguments not supplied for function {node.name}")
                idx += 1
            else:
                self.variables[arg.arg] = value


        self.setup_exit = self.builder.branch(self.entry_block)
        self.builder.position_at_start(self.entry_block)

        for instruction in node.body:
            self.generate(instruction)

        if not self.builder._block.is_terminated:
            self.builder.branch(self.exit_block)

        self.builder.position_at_start(self.exit_block)

        if self.return_value is void:
            self.builder.ret_void()
        else:
            self.builder.ret(self.get_value(self.return_value))

    def visit_Return(self, node: ast.Return):
        if node.value is None:
            return

        return_value: JitObj = self.generate(node.value)
        if return_value is None:
            return

        llvm = self.get_value(return_value)

        if return_value.type != self.return_type:
            if not self.type_unset:
                raise Exception("too many return type redefinitions")
            self.return_type = return_value.type
            self.function_type = ir.FunctionType(llvm.type, [arg.llvm for arg in self.arg_types], False)
            self.function.type = ir.PointerType(self.function_type)
            self.function.ftype = self.function_type
            self.function.return_value.type = llvm.type
            self.function.return_type = return_value.type
            self.type_unset = False

            with self.builder.goto_block(self.entry_block):
                self.builder.position_before(self.setup_exit)

                if isinstance(self.return_type, llvmlite.ir.Type):
                    allocate = self.builder.alloca(self.return_type)
                else:
                    if self.return_type == str:
                        allocate = return_value.llvm
                    else:
                        allocate = self.return_type.alloca(self)
                self.return_value = Variable(self.return_type, allocate, None)

        self.builder.store(llvm, self.return_value.llvm)
        self.builder.branch(self.exit_block)

    def visit_Constant(self, node: ast.Constant):
        value = node.value
        if len(self.type_targets) and self.type_targets[0]:
            default_type = self.type_targets[0]
        else:
            default_type = type_conversions(value.__class__)

        if not default_type:
            raise Exception(f"Type {type(node.value)} not supported yet!")

        if self.type_targets and self.type_targets[0] is not None:
            if not isinstance(self.type_targets[0], PrimitiveType):
                if type(node.value) != self.type_targets[0]:
                    raise Exception(f"Can't coerce {type(node.value)} to {self.type_targets[0]}")

        if default_type == str:
            val = ir.Constant(ir.ArrayType(ir.IntType(8), len(value) + 2), bytearray(value.encode("utf8")))
        else:
            val = ir.Constant(default_type.llvm, value)
        return Value(default_type, val, node)

    def create_name(self, var_name, var_value):
        with self.builder.goto_block(self.setup_block):
            if isinstance(var_value, ArrayType):
                arg_type = objectpointer(var_value)
                var = Variable(arg_type, arg_type.llvm, var_name)
                self.variables[var_name.id] = var
                return var
            elif isinstance(var_value.type, llvmlite.ir.Type):
                allocate = self.builder.alloca(var_value.type)
            else:
                if var_value.type == str:
                    str_ = var_value.llvm.constant.decode("utf8")
                    str_ += "\n\0"
                    s_const = ir.Constant(ir.ArrayType(ir.IntType(8), len(str_)), bytearray(str_.encode("utf8")))
                    global_str = ir.GlobalVariable(self.module, s_const.type, name=f"str_{self.help_cont}")
                    self.help_cont += 1
                    global_str.linkage = 'internal'
                    global_str.global_constant = True
                    global_str.initializer = s_const
                    allocate = global_str
                else:
                    allocate = var_value.type.alloca(self)
        reference = Variable(var_value.type, allocate, var_name)
        if isinstance(var_name, ast.Subscript):
            self.variables[var_name.value.id] = reference
        else:
            self.variables[var_name.id] = reference
        return reference

    def visit_Name(self, node: ast.Name):
        var_reference = self.variables.get(node.id)
        if var_reference:
            return var_reference

        # if not in the dict create it
        var_reference = self.python_mod.__dict__.get(node.id)

        if var_reference:
            new_node = ast.Constant(value=var_reference)
            new_value = self.generate(new_node)
            self.create_name(node, new_value)
            return new_value

        return None

    def visit_Dict(self, node: ast.Dict):
        keys = list(map(self.generate, node.keys))
        values = list(map(self.generate, node.values))
        aaa = 3

        return None

    def visit_Assign(self, node: Union[ast.Assign, ast.AnnAssign]):  # add AnnAssign
        if hasattr(node, 'targets'):
            var_name: ast.Name = node.targets[0]
        else:
            var_name: ast.Name = node.target
        var_reference: JitObj = self.generate(var_name)
        if isinstance(node, ast.AnnAssign):
            type_target = self.get_annotation(node.annotation)
        else:
            if var_reference is None:
                type_target = None
            else:
                type_target = var_reference.type

        with self.type_target(type_target):
            value: JitObj = self.generate(node.value)

        if not var_reference:
            reference = self.create_name(var_name, value)
        else:
            reference = var_reference

        if isinstance(reference.type, PointerType):
            if hasattr(value, 'type') and reference.type.pointee != value.type:
                raise Exception("mismatched types:", reference.type.pointee, value.type)
        elif reference.type != value.type:
            # try to cast
            try:
                reference = self.create_name(var_name, value)
            except RuntimeError as e:
                raise Exception("mismatched types:", reference.type, value.type)

        if isinstance(value, ArrayType):
            value = reference

        value_to_put = self.get_value(value)

        if isinstance(value_to_put.type, ir.ArrayType):
            return None

        return self.builder.store(value_to_put, reference.llvm)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        return self.visit_Assign(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        bin_op = ast.BinOp(left=node.target, right=node.value, op=node.op)
        assign = ast.Assign(targets=[node.target], value=bin_op)
        return self.generate(assign)

    def visit_BinOp(self, node: ast.BinOp):
        lhs: JitObj = self.generate(node.left)

        with self.type_target(lhs.type):
            rhs: JitObj = self.generate(node.right)

        lhs_value = self.get_value(lhs)
        rhs_value = self.get_value(rhs)

        resulted_type = lhs.type

        if lhs.type != rhs.type:
            if (isinstance(lhs.type, BaseInt) and isinstance(rhs.type, BaseFloat)) or \
                (isinstance(lhs.type, BaseFloat) and isinstance(rhs.type, BaseInt)):
                if isinstance(lhs.type, BaseInt):
                    resulted_type = rhs.type
                    if isinstance(lhs_value, ir.Constant):
                        lhs_value = ir.Constant(rhs.type.llvm, lhs_value.constant)
                    else:
                        if isinstance(lhs.type, SignedInt):
                            cast = self.builder.sitofp(lhs_value, llvmlite.ir.types.DoubleType())
                        else:
                            cast = self.builder.uitofp(lhs_value, llvmlite.ir.types.DoubleType())
                        new_var = self.get_value(cast)
                        lhs_value = self.get_value(new_var)
                else:
                    resulted_type = lhs.type
                    if isinstance(rhs_value, ir.Constant):
                        rhs_value = ir.Constant(lhs.type.llvm, rhs_value.constant)
                    else:
                        if isinstance(rhs.type, SignedInt):
                            cast = self.builder.sitofp(rhs_value, llvmlite.ir.types.DoubleType())
                        else:
                            cast = self.buidler.uitofp(rhs_value, llvmlite.ir.types.DoubleType())
                        new_var = self.get_value(cast)
                        rhs_value = self.get_value(new_var)
            elif self.test_no_class(lhs.type, rhs.type):
                raise Exception(f"Mismatched types for operation! {lhs.type} /= {rhs.type}")

        op_type = node.op.__class__.__name__
        op = getattr(resulted_type, f"do_{op_type}", None)
        if not op:
            raise Exception(f"Operation /{op_type}/ not supported yet!")
        result = op(self, lhs_value, rhs_value)
        return Value(resulted_type, result, node)

    def visit_UnaryOp(self, node:ast.UnaryOp):
        lhs: JitObj = self.generate(node.operand)
        op_type = node.op.__class__.__name__
        op = getattr(lhs.type, f"do_{op_type}", None)

        if not op:
            raise Exception(f"Operation /{op_type}/ not supported yet!")

        result = op(self, self.get_value(lhs))
        return Value(lhs.type, result, node)

    def visit_BoolOp(self, node: ast.BoolOp):
        lhs_value = self.get_value(self.generate(node.values[0]))
        rhs_value = self.get_value(self.generate(node.values[1]))

        if isinstance(node.op, ast.And):
            result = self.builder.and_(lhs_value, rhs_value)
        elif isinstance(node.op, ast.Or):
            result = self.builder.or_(lhs_value, rhs_value)
        else:
            raise NotImplementedError
        return Value(bul, result, None)

    def visit_Expr(self, node: ast.Expr):
        return self.generate(node.value)

    def visit_Compare(self, node: ast.Compare):
        lhs: JitObj = self.generate(node.left)

        with self.type_target(lhs.type):
            rhs: JitObj = self.generate(node.comparators[0])

        if lhs.type != rhs.type:
            raise Exception(f"Mismatched types for operation! {lhs.type} /= {rhs.type}")

        op_type = node.ops[0].__class__.__name__
        op = getattr(lhs.type, f"do_{op_type}", None)

        result = op(self, self.get_value(lhs), self.get_value(rhs))
        return Value(bul, result, node)

    def visit_If(self, node: ast.If):
        then_block = self.builder.append_basic_block("then")
        else_block = self.builder.append_basic_block("else")
        end_block = self.builder.append_basic_block("end")

        clause = self.generate(node.test)
        clause_llvm = self.to_bool(self.get_value(clause), clause)

        self.builder.cbranch(clause_llvm, then_block, else_block)
        self.builder.position_at_start(then_block)

        for new_node in node.body:
            self.generate(new_node)
        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)

        self.builder.position_at_start(else_block)
        for new_node in node.orelse:
            self.generate(new_node)
        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)
        self.builder.position_at_start(end_block)

    def visit_While(self, node: ast.While):
        loop_block = self.builder.append_basic_block("while")
        end_block = self.builder.append_basic_block("while_end")

        self.loop_stack.append(loop_block)
        self.break_stack.append(end_block)

        self.builder.branch(loop_block)
        self.builder.position_at_start(loop_block)
        for new_node in node.body:
            self.generate(new_node)
        clause = self.generate(node.test)
        clause_llvm = self.to_bool(self.get_value(clause), clause)

        self.builder.cbranch(clause_llvm, loop_block, end_block)
        self.builder.position_at_start(end_block)

    def visit_For(self, node: ast.For):
        for_init = self.builder.append_basic_block("for_init")
        test_block = self.builder.append_basic_block("for_cond")
        loop_block = self.builder.append_basic_block("for")
        end_block = self.builder.append_basic_block("for_end")

        self.loop_stack.append(loop_block)
        self.break_stack.append(end_block)

        if node.iter.func.id in {"range"}:
            args = list(map(self.generate, node.iter.args))
        else:
            raise NotImplementedError

        start, stop, step = 0, 0, 0
        len_args = len(args)
        if len_args == 1:
            start = 0
            stop = args[0]
            step = 1
        elif len_args == 2:
            start = args[0]
            stop = args[1]
            step = 1
        elif len_args == 3:
            start = args[0]
            stop = args[1]
            step = args[2]

        if start == 0:
            incr = self.create_name(node.target, Value(i64, ir.Constant(ir.IntType(64), 0), ast.Constant(value=0)))
            incr_val = 0
        else:
            incr_val = self.get_value(start)
            incr = self.create_name(node.target, ir.Constant(ir.IntType(64), incr_val))

        if isinstance(stop.llvm, ir.AllocaInstr):
            stop_val = self.get_value(stop)
            self.create_name(ast.Name("stop"), ir.Constant(ir.IntType(64), stop_val))
        else:
            self.create_name(ast.Name("stop"), ir.Constant(ir.IntType(64), stop.llvm.constant))
            stop_val = stop.llvm.constant

        if step == 1:
            self.create_name(ast.Name("step"), ir.Constant(ir.IntType(64), 1))
            step_val = 1
        else:
            step_val = self.get_value(step)
            self.create_name(ast.Name("step"), ir.Constant(ir.IntType(64), step_val))

        self.builder.branch(for_init)
        self.builder.position_at_start(for_init)

        if isinstance(incr_val, ir.LoadInstr):
            self.builder.store(incr_val, incr.llvm)
        else:
            self.builder.store(ir.Constant(ir.IntType(64), incr_val), incr.llvm)

        if isinstance(stop_val, ir.LoadInstr):
            self.builder.store(stop_val, self.variables["stop"].llvm)
        else:
            self.builder.store(ir.Constant(ir.IntType(64), stop_val), self.variables["stop"].llvm)

        if isinstance(step_val, ir.LoadInstr):
            self.builder.store(step_val, self.variables["step"].llvm)
        else:
            self.builder.store(ir.Constant(ir.IntType(64), step_val), self.variables["step"].llvm)

        self.builder.branch(test_block)
        self.builder.position_at_start(test_block)
        condition = self.builder.icmp_signed("<", self.get_value(incr), self.get_value(self.variables["stop"]))
        self.builder.cbranch(condition, loop_block, end_block)

        self.builder.position_at_start(loop_block)

        for instr in node.body:
            self.generate(instr)

        sum = self.builder.add(self.get_value(incr), self.get_value(self.variables["step"]))
        self.builder.store(sum, incr.llvm)

        self.builder.branch(test_block)

        self.builder.position_at_start(end_block)

    def visit_Break(self, node: ast.Break):
        if not self.break_stack:
            raise Exception("Break encountered outside of loop")
        break_target = self.break_stack.pop()
        self.builder.branch(break_target)

    def visit_Continue(self, node: ast.Continue):
        loop_target = self.loop_stack.pop()
        self.builder.branch(loop_target)

    def visit_Call(self, node: ast.Call):
        # with one argument now

        values = []
        for new_node in node.args:
            gen = self.generate(new_node)
            if isinstance(gen.llvm, ir.GlobalVariable):
                values.append(gen)
            else:
                val = self.get_value(gen)
                values.append(val)

        if hasattr(node.func, 'func') and node.func.func.attr == "JArray":
            if node.func.args[0].attr == "i64":
                ty = i64
            else:
                ty = f64
            inst_ar = JArray(ty, node.func.args[1].value)
            return inst_ar

        function_name = node.func.id

        # check if the function exists
        call = self.module.globals.get(function_name, None)
        if call:
            tmp = self.builder.call(call, values)
            ty = i64
            if isinstance(tmp.type, ir.DoubleType):
                ty = f64
            # void can t be possible
            var = Variable(ty, tmp, ast.Name(f"tmp_{self.help_cont}"))
            tmp_var = self.create_name(ast.Name(f"tmp_{self.help_cont}"), var)
            self.help_cont += 1
            self.builder.store(tmp, tmp_var.llvm)
            return tmp_var

        # maybe is in standard_func
        call = standard_func.make(function_name)
        if call:
            return call(self, values)

        raise Exception(f"No such function {function_name}")

    def visit_Subscript(self, node: ast.Subscript):
        value = self.generate(node.value)
        val_llvm = value.llvm

        slice = self.generate(node.slice)
        index = self.get_value(slice)
        ptr = self.builder.gep(val_llvm, [self.zero, index])

        if isinstance(value.type, ObjectPointer):
            return Variable(value.type.pointee.base_type, ptr, None)

        if value.type == str:
            return Variable(i8, ptr, None)

        return Variable(value.type.base_type, ptr, None)

    def visit_Attribute(self, node: ast.Attribute):
        raise NotImplementedError


jit_generator = JitGenerator()

