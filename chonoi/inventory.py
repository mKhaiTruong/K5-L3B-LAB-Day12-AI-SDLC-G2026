"""File kho. v1.2 (TICKET-03): {"items": [{"id","kind","fresh"}]}; v1.0/v1.1: {"items": {kind: số nguyên >= 0}}.

Đọc: từ chối sai schema / id lạ / số âm (BadInput -> mã 2).
Ghi: bỏ mục bằng 0, qua file tạm cùng thư mục rồi thay thế, byte-ổn-định.
"""

import json
import os
import tempfile

from .errors import BadInput

KINDS = ("ca_loc", "ca_linh", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")  # v1.1: 6 nguyên liệu
KINDS_P1 = KINDS  # tên cũ, giữ để không vỡ import


def validate_items(items, kinds=KINDS_P1):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def uses_item_schema(version) -> bool:
    """Contract >= 1.2 dùng kho cá thể `{"items":[{id,kind,fresh}]}`; cũ hơn dùng kho đếm."""
    major, minor = (int(x) for x in str(version).split(".")[:2])
    return (major, minor) >= (1, 2)


def read_inventory(path: str, version="1.2", kinds=KINDS_P1):
    """Đọc file kho theo schema của `contract_version`.

    Args:
        path: đường dẫn file kho (`--inventory`).
        version: `contract_version` đang chạy.
        kinds: danh mục nguyên liệu hợp lệ.

    Returns:
        v1.2: danh sách cá thể nội bộ `{"id","kind","u"}` (xem `chonoi.fresh`), giữ thứ tự file.
        v1.0/v1.1: dict đếm kind -> số lượng.

    Raises:
        BadInput: sai schema, kind lạ, id trùng, fresh ngoài miền, hoặc kho đếm khi chạy v1.2 (mã 2).
    """
    from .fresh import parse_items  # tránh import vòng (fresh -> ids)

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if uses_item_schema(version):
        return parse_items(data["items"], "file kho.items", kinds)
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list):
    """Giỏ -> nội dung kho để bàn giao.

    Returns:
        Giỏ cá thể (v1.2): mảng `{"id","kind","fresh"}` sắp theo id.
        Giỏ kind (v1.0/v1.1): object đếm sắp theo kind.
    """
    if hold and isinstance(hold[0], dict):
        from .fresh import by_id, public
        return [public(it) for it in by_id(hold)]
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items):
    """Ghi file kho nguyên tử (file tạm cùng thư mục rồi thay thế).

    Args:
        path: đích `--inventory-out`.
        items: mảng cá thể (dạng nội bộ hoặc public, v1.2; ghi theo id, fresh đủ chính xác để đọc lại)
            hoặc dict đếm (v1.0/v1.1).
    """
    if isinstance(items, list):
        from .fresh import by_id, public
        items = [public(it) if "u" in it else it for it in by_id(items)]
    else:
        items = {k: items[k] for k in sorted(items) if items[k] > 0}
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": items}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
