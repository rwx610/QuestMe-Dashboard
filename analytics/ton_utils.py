import base64, struct
from tonsdk.boc import Cell


def extract_operation_type(tx: dict) -> str:
    try:
        in_msg = tx.get("in_msg") or {}
        msg_data = in_msg.get("msg_data") or {}
        data_type = msg_data.get("@type")

        if data_type == "msg.dataText":
            return "TextComment"

        if data_type == "msg.dataRaw":
            body_b64 = msg_data.get("body")
            if not body_b64:
                return "EmptyBody"

            try:
                boc = base64.b64decode(body_b64)
                cell = Cell.one_from_boc(boc)
                sl = cell.begin_parse()
                op_code_int = sl.read_uint(32)
                op_code_hex = hex(op_code_int)

                match op_code_hex:
                    case "0x0" | "0x00000000":
                        return "Transfer"
                    case _:
                        return op_code_hex
            except Exception as e:
                print(f"[Decode error] body BOC: {e}")
                return "InvalidBOC"

        return "Unknown"

    except Exception as e:
        print(f"[Main error] extract_operation_type: {e}")
        return "Unknown"
    

def body_is_jetton_transfer(b64_body: str) -> bool:
    JETTON_OPCODE_TRANSFER = 0xF8A7EA5
    try:
        data = base64.b64decode(b64_body)
        (op,) = struct.unpack(">I", data[:4])  # big‑endian uint32
        return op == JETTON_OPCODE_TRANSFER
    except Exception:
        return False