"""D2 TDD — ClinicalContextFlag schema validation."""
from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError


class _Wrapper(BaseModel):
    flag: "ClinicalContextFlag"  # type: ignore[name-defined]


def test_valid_tca():
    from app.schemas.clinical import ClinicalContextFlag
    from pydantic import TypeAdapter
    ta: TypeAdapter[ClinicalContextFlag] = TypeAdapter(ClinicalContextFlag)
    assert ta.validate_python("tca") == "tca"


def test_valid_red_s():
    from app.schemas.clinical import ClinicalContextFlag
    from pydantic import TypeAdapter
    ta: TypeAdapter[ClinicalContextFlag] = TypeAdapter(ClinicalContextFlag)
    assert ta.validate_python("red_s") == "red_s"


def test_valid_ots_nfor():
    from app.schemas.clinical import ClinicalContextFlag
    from pydantic import TypeAdapter
    ta: TypeAdapter[ClinicalContextFlag] = TypeAdapter(ClinicalContextFlag)
    assert ta.validate_python("ots_nfor") == "ots_nfor"


def test_valid_none():
    from app.schemas.clinical import ClinicalContextFlag
    from pydantic import TypeAdapter
    ta: TypeAdapter[ClinicalContextFlag] = TypeAdapter(ClinicalContextFlag)
    assert ta.validate_python(None) is None


def test_invalid_value_raises():
    from app.schemas.clinical import ClinicalContextFlag
    from pydantic import TypeAdapter
    ta: TypeAdapter[ClinicalContextFlag] = TypeAdapter(ClinicalContextFlag)
    with pytest.raises(Exception):
        ta.validate_python("unknown_flag")


def test_flag_in_pydantic_model():
    from app.schemas.clinical import ClinicalContextFlag
    from pydantic import BaseModel as _BM
    class _M(_BM):
        flag: ClinicalContextFlag = None
    m = _M(flag="tca")
    assert m.flag == "tca"
    m2 = _M()
    assert m2.flag is None
