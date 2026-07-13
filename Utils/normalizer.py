# =========================
# NORMALIZE MD01 (DEALER)
# =========================
def normalize_MD01(vData: dict) -> dict:
    if "MainDealers" in vData:
        return vData
    return {
        "SyncCode": vData.get("SyncCode", ""),
        "MainDealers": [
            {
                "MainDealerCode"   : vData.get("MainDealerCode", ""),
                "MainDealerName"   : vData.get("MainDealerName", ""),
                "MainDealerCodeHSO": vData.get("MainDealerCodeHSO", ""),
                "Dealers"          : vData.get("Dealers", [])
            }
        ]
    }


# =========================
# NORMALIZE PR01 (POLREG)
# =========================
def normalize_PR01(vData: dict) -> dict:
    if "MainDealers" in vData:
        return vData
    return {
        "SyncCode": vData.get("SyncCode", ""),
        "MainDealers": [
            {
                "MainDealerCode": vData.get("MainDealerCode", ""),
                "Dealers"       : vData.get("Dealers", [])
            }
        ]
    }


# =========================
# NORMALIZE UMCM (CATALOGUE)
# =========================
def normalize_UMCM(vData: dict) -> dict:
    if "MainDealers" in vData:
        return vData
    return {
        "SyncCode"  : vData.get("SyncCode", ""),
        "CutoffDate": vData.get("CutoffDate", ""),
        "CutoffTime": vData.get("CutoffTime", ""),
        "MainDealers": [
            {
                "MainDealerCode": vData.get("MainDealerCode", ""),
                "UnitTypes"     : vData.get("UnitTypes", [])
            }
        ]
    }


# =========================
# NORMALIZE DISPATCHER
# =========================
_vNormalize_Map = {
    "MD01": normalize_MD01,
    "PR01": normalize_PR01,
    "UMCM": normalize_UMCM,
}


def normalize(vSync: str, vData: dict) -> dict:
    vFunc = _vNormalize_Map.get(vSync)
    if vFunc:
        return vFunc(vData)
    return vData