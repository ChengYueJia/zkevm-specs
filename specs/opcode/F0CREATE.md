# CREATE & CEATE2 opcode

## Procedure

Both `Create` and `Create2` can create a new contract.

* `Create` - Create a new account with associated code
* `Create2` - Create a new account with associated code at a predictable address

### EVM behavior

1. Pop from the stack.
   - `value`: value in `wei` to send to the new account.
   - `offset`: byte offset in the memory in bytes, the initialisation code for the new account.
   - `length`: byte size to copy (size of the initialisation code).
   - `salt`: 32-byte value used to create the new account at a deterministic address.
     - This is poped for `Create2` opcode


2. Before switching call context to the new one, it does several things:

   1. Expand memory
   2. Add `sender` into access list
   3. Calculate `gas_cost` and check `gas_left` is enough
   4. Calculate `callee_gas_left` for new context by rule in EIP150
   5. Check `depth` is less than `1024`
   6. Check `offset` could have `initcode`
   
 
3. After switching call context, it does:
   1. Transfer `value` 
   2. Execution
      - Calculate the `contract_addr`
        - For `Create`
        ```
        address = keccak256(rlp([sender_address,sender_nonce]))
        ```
        - For `Create2`
        ```
        address = keccak256(0xff + sender_address + salt + keccak256(initialisation_code))[12:]
        ```
      - Create Contract
      - Execute analyzed EVM bytecode using provided Host context
   3. Copy `return_data` of execution to caller specified memory chunk
   4. Push to the stack.
      - `address`: the address of the deployed contract. if the deployment failed, will throw error.


## Constraints

1. opId == 0xF0
2. State transition:
    - gc + 2
    - stack_pointer - 1
    - pc + 1
    - gas + 2
3. Lookups: 2
    - ReturnDataLength is in the rw table {call context, call ID, ReturnDataLength}.
    - ReturnDataLength is on top of stack.

## Exceptions

1. Not enough gas.
2. Not enough values on the stack.
3. The current execution context is from a STATICCALL.

## Code

Please refer to `src/zkevm_specs/evm/execution/callop.py`.
