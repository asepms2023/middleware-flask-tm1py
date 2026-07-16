# =========================
# IMPORTS
# =========================
from Validation.validation_rules import RULES
from Utils.normalizer import normalize


# =========================
# FIND FIELD POSITION IN RAW JSON
# =========================
def find_field_position(vRaw: str, vField: str, vOccurrence: int = 1):
    vLines = vRaw.splitlines()
    vCount = 0
    for vIdx, vLine in enumerate(vLines, start=1):
        vCol = vLine.find(f'"{vField}"')
        if vCol != -1:
            vCount += 1
            if vCount == vOccurrence:
                vColon_Pos = vLine.find(":", vCol + len(vField) + 2)
                if vColon_Pos == -1:
                    return vIdx, vCol + 1

                vValue_Pos = vColon_Pos + 1
                while vValue_Pos < len(vLine) and vLine[vValue_Pos] in (" ", "\t"):
                    vValue_Pos += 1

                if vValue_Pos >= len(vLine):
                    return vIdx, vCol + 1

                return vIdx, vValue_Pos + 1
    return None, None


# =========================
# CHECK SINGLE FIELD
# =========================
def check_field(vVal, vRequired, vExpected_Type, vField, vRaw: str = "", vOccurrence: int = 1):

    if vRequired and (vVal is None or vVal == ""):
        vLine, vCol = find_field_position(vRaw, vField, vOccurrence)
        vPos = f" (Line {vLine}, Col {vCol})" if vLine else ""
        return f"{vField} is invalid{vPos}"

    if vVal not in (None, "") and not isinstance(vVal, vExpected_Type):
        vType_Name = {
            str: "string",
            int: "integer"
        }.get(vExpected_Type, vExpected_Type.__name__)

        vLine, vCol = find_field_position(vRaw, vField, vOccurrence)
        vPos = f" (Line {vLine}, Col {vCol})" if vLine else ""
        return f"{vField} must be a {vType_Name}{vPos}"

    return None


# =========================
# VALIDATE
# =========================
def validate(vData, vRaw: str = "", vExpected_Sync: str = ""):

    if not isinstance(vData, dict):
        return "Invalid JSON"

    # =========================
    # VALIDASI SYNCCODE
    # =========================
    vSync = vData.get("SyncCode")
    if not vSync or str(vSync).strip() == "":
        return "SyncCode is invalid"

    if vExpected_Sync and vSync != vExpected_Sync:
        return f"SyncCode '{vSync}' is not valid for this endpoint"

    if vSync not in RULES:
        return "SyncCode not supported"

    # =========================
    # NORMALIZE
    # =========================
    vData = normalize(vSync, vData)
    vRule = RULES[vSync]

    # =========================
    # HEADER VALIDATION
    # =========================
    for vField, vCfg in vRule["header"].items():
        if vField == "SyncCode":
            continue
        vVal = vData.get(vField)
        vErr = check_field(vVal, vCfg.get("required", False), vCfg["type"], vField, vRaw)
        if vErr:
            return vErr

    # =========================
    # DETAIL VALIDATION
    # =========================
    vDetail_Key = vRule.get("detail_key")
    vDetails    = vData.get(vDetail_Key)

    if not isinstance(vDetails, list) or len(vDetails) == 0:
        return f"{vDetail_Key} is invalid"
    nSub_Occurrence = 0

    for nIdx, vItem in enumerate(vDetails, start=1):
        if not isinstance(vItem, dict):
            return f"{vDetail_Key} is invalid"

        for vField, vCfg in vRule["detail"].items():
            vVal = vItem.get(vField)
            vErr = check_field(vVal, vCfg.get("required", False), vCfg["type"], vField, vRaw, vOccurrence=nIdx)
            if vErr:
                return vErr

        # =========================
        # SUB DETAIL VALIDATION
        # =========================
        vSub_Key = vRule.get("sub_detail_key")
        if vSub_Key:
            vSub_Details = vItem.get(vSub_Key)

            if not isinstance(vSub_Details, list) or len(vSub_Details) == 0:
                return f"{vSub_Key} is invalid"

            for vSub_Item in vSub_Details:
                nSub_Occurrence += 1

                if not isinstance(vSub_Item, dict):
                    return f"{vSub_Key} is invalid"

                for vField, vCfg in vRule["sub_detail"].items():
                    vVal = vSub_Item.get(vField)
                    vErr = check_field(vVal, vCfg.get("required", False), vCfg["type"], vField, vRaw, vOccurrence=nSub_Occurrence)
                    if vErr:
                        return vErr

    return None