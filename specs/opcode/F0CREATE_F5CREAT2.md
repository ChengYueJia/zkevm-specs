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

4. Calculate Gas cost
   1. For `Create`
   ```
   gas_cost = 32000 + memory_expansion_cost + code_deposit_cost
   ```
   
   2. For `Create2`
   ```
   gas_cost = 32000 + 6 * data_size_words + memory_expansion_cost + code_deposit_cost
   ```
   
   * Tips
     
     - `data_size_words`:
     ```
     data_size_words = (data_size + 31) / 32
     ```

     - `code_deposit_cost`:
     ```
     code_deposit_cost = 200 * deployed_code_size
     ```
     
     - `memory_expansion_cost`:

     ```
     memory_size_word = (memory_byte_size + 31) / 32
     memory_cost = (memory_size_word ** 2) / 512 + (3 * memory_size_word)
     
     memory_expansion_cost = new_memory_cost - last_memory_cost
     ```

## Constraints

1. opcodeId checks
   - opId === OpcodeId(0xF0) for `Create`
   - opId === OpcodeId(0xF5) for `Create2`
2. Calculate the `contract_addr`
   - For `Create`
   ```
    address == keccak256(rlp([sender_address,sender_nonce]))
    ```
   - For `Create2`
   ```
   address == keccak256(0xff + sender_address + salt + keccak256(initialisation_code))[12:]
   ```
2. State Transitions:
   - rw_counter + 4 for `Create`, rw_counter + 5 for `Create2`,
   - stack_pointer + 3
   - pc + 1
   - gas + gas_cost
   
3. Lookups:
   - `value` is at the top of the stack
   - `offset` is at the second position of the stack
   - `size` is at the third position of the stack
   - `salt` is at the forth position of the stack

## Exceptions

1. Not enough gas.
2. Not enough values on the stack.
3. The current execution context is from a STATICCALL.

## Code

Please refer to `src/zkevm_specs/evm/execution/create.py`.
