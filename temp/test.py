from tonsdk.boc import Cell
import base64

def extract_op_code(tx: dict) -> str:
    try:
        data_b64 = tx.get("data")
        if not data_b64:
            raise ValueError("No 'data' field found in transaction.")

        boc_bytes = base64.b64decode(data_b64)
        root_cell = Cell.one_from_boc(boc_bytes)

        # используем begin_parse для чтения 32 бит
        slice = root_cell.begin_parse()
        op_code = slice.read_uint(32)

        return f"op_code: {hex(op_code)}"
    except Exception as e:
        return f"Error extracting op_code: {e}"

# пример
transaction = {
    "data": "te6cckECBwEAAZsAA7V6f2EILq03KQOpmKx8m/CsT1FA09qVXxUCs1auYj9ES2AAA1ma1u+wFb0N1oU/uJQoKsHyFa9+HcQX3LjVggUQ0OiDTrl7QtSAAANZPF+puBaGPrTQABRgyNroAQIDAQGgBACCcgp5SX4FVSUKlyN6fT0tPtq4/YqgQUlhCqRLe8RH7+Nb1s0QAOThNEleXAFYyIXKXp8YL2Gb26XNOjZwW4YOQdwCGQyOmckAvrwgGGDBjhEFBgC/SAAC8/877th5cPQ/rLThdrL8DOoNbbuA4tcYKAp9Y9iOYQAp/YQgurTcpA6mYrHyb8KxPUUDT2pVfFQKzVq5iP0RLZAL68IABggjWgAAazNagmiE0MfWjgAAAAAZG5jAAJ5Ae+wHoSAAAAAAAAAAAB0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFvAAAAAAAAAAAAAAAABLUUtpEnlC4z33SeGHxRhIq/htUa7i3D8ghbwxhQTn44EX0VB4A=="
}

print(dir(slice))
print(extract_op_code(transaction))

