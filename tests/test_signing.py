# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

import base64
from app.caltopo import sign_request


def test_signing_is_deterministic():
    secret=base64.b64encode(b"secret-key").decode()
    a=sign_request("GET","/api/v1/map/ABC/since/0",123456,"",secret)
    b=sign_request("GET","/api/v1/map/ABC/since/0",123456,"",secret)
    assert a == b
    assert isinstance(base64.b64decode(a), bytes)
