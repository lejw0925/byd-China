"""HVAC status endpoint.

Endpoint:
  - /control/getStatusNow
"""

from __future__ import annotations

from pybyd_china._api._common import ENDPOINT_NOT_SUPPORTED_CODES, build_inner_base, post_token_json
from pybyd_china._transport import Transport
from pybyd_china.config import BydConfig
from pybyd_china.models.hvac import HvacStatus
from pybyd_china.session import Session

_ENDPOINT = "/control/getStatusNow"


async def fetch_hvac_status(
    config: BydConfig,
    session: Session,
    transport: Transport,
    vin: str,
) -> HvacStatus:
    """Fetch current HVAC/climate control status for a vehicle."""
    inner = build_inner_base(config, vin=vin)
    decoded = await post_token_json(
        endpoint=_ENDPOINT,
        config=config,
        session=session,
        transport=transport,
        inner=inner,
        vin=vin,
        not_supported_codes=ENDPOINT_NOT_SUPPORTED_CODES,
    )
    return HvacStatus.model_validate(decoded)
