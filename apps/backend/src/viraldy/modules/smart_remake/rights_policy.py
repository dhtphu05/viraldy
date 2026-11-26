"""Versioned seller attestation; acceptance is a declaration, never verified ownership."""

from typing import Literal

RightsPolicyVersion = Literal["smart-remake-media-rights-v1"]
RIGHTS_POLICY_VERSION: RightsPolicyVersion = "smart-remake-media-rights-v1"
RIGHTS_POLICY_STATEMENT = (
    "Tôi xác nhận sở hữu hoặc có đủ quyền sử dụng video và ảnh đã tải lên để tạo video AI "
    "phục vụ quảng bá sản phẩm. Tôi chịu trách nhiệm về quyền sử dụng các tư liệu này."
)
