from ...util import (
    EMPTY_CODE_HASH,
    FQ,
    GAS_COST_ACCOUNT_COLD_ACCESS,
    GAS_COST_CALL_WITH_VALUE,
    GAS_COST_NEW_ACCOUNT,
    GAS_COST_WARM_ACCESS,
    GAS_STIPEND_CALL_WITH_VALUE,
    N_BYTES_ACCOUNT_ADDRESS,
    N_BYTES_GAS,
    RLC, keccak256, Expression,
)
from ..instruction import Instruction, Transition
from ..opcode import Opcode
from ..table import RW, CallContextFieldTag, AccountFieldTag
import rlp  # type: ignore

static_cost = 32000


def create(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)
    instruction.responsible_opcode_lookup(opcode)

    # CHECK is_create2
    is_create2_call, _ = instruction.pair_select(opcode, Opcode.CREATE, Opcode.CREATE2)
    is_create2 = instruction.select(
        is_create2_call, FQ(1), instruction.call_context_lookup(CallContextFieldTag.IsCreate2)
    )

    # Lookup values from stack
    value = instruction.stack_pop()
    memory_offset_word = instruction.stack_pop()
    code_size_word = instruction.stack_pop()
    if is_create2:
        salt = instruction.stack_pop()
    contract_addr = instruction.stack_push()

    # reversion_info = instruction.reversion_info()
    caller_address = instruction.call_context_lookup(CallContextFieldTag.CallerAddress)
    caller_nonce = instruction.account_read(caller_address, AccountFieldTag.Nonce)

    depth = instruction.call_context_lookup(CallContextFieldTag.Depth)

    ### 1.before switching call context
    # Verify depth is less than 1024
    instruction.range_lookup(depth, 1024)

    # calculate contract address
    if is_create2:
        gen_rlc = rlp(bytes(caller_address), caller_nonce.expr())
    else:
        code_hash = instruction.curr.code_hash
        # contract_address_gen = keccak256(bytes(0xff), bytes(caller_address), salt, bytes(code_hash))
        inic_code_keccak256 = instruction.keccak_lookup(bytes(code_hash, code_size_word))
        gen_rlc = RLC(bytes(0xff), bytes(caller_address), salt.int_value, inic_code_keccak256.expr())

    contract_address_gen = instruction.keccak_lookup(RLC(256), gen_rlc)

    # expand memory & calculate gas
    gas_cost = create_cost_calcute(instruction, memory_offset_word, code_size_word, is_create2)

    # constraints: address
    instruction.constrain_equal(contract_addr.expr(), contract_address_gen)

    # Verify transfer
    instruction.transfer(
        caller_address, contract_addr, value
    )

    # Verify transfer
    instruction.transfer(caller_address, contract_addr, value)

    if is_create2:
        rw_counter = 5
    else:
        rw_counter = 4

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(instruction.rw_counter_offset + rw_counter),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.delta(3),
        dynamic_gas_cost=gas_cost,
    )


def create_cost_calcute(instruction: Instruction, memory_offset_word: RLC, code_size_word: RLC,
                        is_create2: Expression) -> FQ:
    memory_offset, code_size = instruction.memory_offset_and_length(memory_offset_word, code_size_word)

    next_memory_size, memory_expansion_gas_cost = instruction.memory_expansion_constant_length(
        memory_offset, code_size
    )
    code_deposit_cost = instruction.code_deposit_cost(code_size)

    gas_cost = static_cost + memory_expansion_gas_cost + code_deposit_cost
    if is_create2:
        gas_cost += FQ(6) * code_size

    return gas_cost
