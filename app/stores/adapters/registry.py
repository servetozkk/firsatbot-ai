from __future__ import annotations

from app.stores.adapters.amazon import AMAZON_ADAPTER
from app.stores.adapters.base import StoreAdapter
from app.stores.adapters.gaminggen import GAMINGGEN_ADAPTER
from app.stores.adapters.hepsiburada import HEPSIBURADA_ADAPTER
from app.stores.adapters.mediamarkt import MEDIAMARKT_ADAPTER
from app.stores.adapters.n11 import N11_ADAPTER
from app.stores.adapters.pazarama import PAZARAMA_ADAPTER
from app.stores.adapters.pttavm import PTTAVM_ADAPTER
from app.stores.adapters.beymen import BEYMEN_ADAPTER
from app.stores.adapters.idefix import IDEFIX_ADAPTER
from app.stores.adapters.teknosa import TEKNOSA_ADAPTER
from app.stores.adapters.turkcellpasaj import TURKCELL_PASAJ_ADAPTER
from app.stores.adapters.vatan import VATAN_ADAPTER
from app.stores.adapters.itopya import ITOPYA_ADAPTER
from app.stores.adapters.incehesap import INCEHESAP_ADAPTER


class StoreAdapterRegistry:
    _adapters = {
        AMAZON_ADAPTER.code: AMAZON_ADAPTER,
        HEPSIBURADA_ADAPTER.code: HEPSIBURADA_ADAPTER,
        TEKNOSA_ADAPTER.code: TEKNOSA_ADAPTER,
        TURKCELL_PASAJ_ADAPTER.code: TURKCELL_PASAJ_ADAPTER,
        GAMINGGEN_ADAPTER.code: GAMINGGEN_ADAPTER,
        MEDIAMARKT_ADAPTER.code: MEDIAMARKT_ADAPTER,
        N11_ADAPTER.code: N11_ADAPTER,
        PAZARAMA_ADAPTER.code: PAZARAMA_ADAPTER,
        PTTAVM_ADAPTER.code: PTTAVM_ADAPTER,
        BEYMEN_ADAPTER.code: BEYMEN_ADAPTER,
        IDEFIX_ADAPTER.code: IDEFIX_ADAPTER,
        VATAN_ADAPTER.code: VATAN_ADAPTER,
        ITOPYA_ADAPTER.code: ITOPYA_ADAPTER,
        INCEHESAP_ADAPTER.code: INCEHESAP_ADAPTER,
    }

    @classmethod
    def get(cls, store_code: str) -> StoreAdapter | None:
        return cls._adapters.get(str(store_code or "").casefold())

    @classmethod
    def registered_codes(cls) -> tuple[str, ...]:
        return tuple(sorted(cls._adapters))
