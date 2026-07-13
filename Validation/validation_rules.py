# =========================
# VALIDATION RULES
# =========================
RULES = {

    # =========================
    # MD01 (DEALER)
    # =========================
    "MD01": {
        "detail_key": "MainDealers",
        "header": {
            "SyncCode": {"type": str, "required": True},
        },
        "detail": {
            "MainDealerCode"   : {"type": str, "required": True},
            "MainDealerName"   : {"type": str, "required": True},
            "MainDealerCodeHSO": {"type": str, "required": True},
        },
        "sub_detail_key": "Dealers",
        "sub_detail": {
            "DealerCode"     : {"type": str, "required": True},
            "DealerName"     : {"type": str, "required": True},
            "DealerAHMCode"  : {"type": str, "required": True},
            "GroupDealerCode": {"type": str, "required": True},
            "GroupDealerName": {"type": str, "required": True},
            "TypeChannel"    : {"type": str, "required": True},
            "AreaQQ"         : {"type": str, "required": False},
            "IsSemiQQ"       : {"type": str, "required": False},
        }
    },

    # =========================
    # PR01 (POLREG)
    # =========================
    "PR01": {
        "detail_key": "MainDealers",
        "header": {
            "SyncCode": {"type": str, "required": True},
        },
        "detail": {
            "MainDealerCode": {"type": str, "required": True},
        },
        "sub_detail_key": "Dealers",
        "sub_detail": {
            "DealerCode": {"type": str, "required": True},
            "PolregCode": {"type": str, "required": True},
            "PolregName": {"type": str, "required": True},
        }
    },

    # =========================
    # WD01 (WORKDAYS)
    # =========================
    "WD01": {
        "detail_key": "Workdays",
        "header": {
            "SyncCode": {"type": str, "required": True},
        },
        "detail": {
            "PeriodYear" : {"type": int, "required": True},
            "PeriodMonth": {"type": int, "required": True},
            "WorkDays"   : {"type": int, "required": True},
        }
    },

    # =========================
    # UMCM (CATALOGUE)
    # =========================
    "UMCM": {
        "detail_key": "MainDealers",
        "header": {
            "SyncCode"  : {"type": str, "required": True},
            "CutoffDate": {"type": str, "required": True},
            "CutoffTime": {"type": str, "required": True},
        },
        "detail": {
            "MainDealerCode": {"type": str, "required": True},
        },
        "sub_detail_key": "UnitTypes",
        "sub_detail": {
            "Material"              : {"type": str, "required": True},
            "Material Description"  : {"type": str, "required": True},
            "ColorCode"             : {"type": str, "required": True},
            "ColorDescription"      : {"type": str, "required": True},
            "CommercialName"        : {"type": str, "required": False},
            "Series"                : {"type": str, "required": True},
            "Segment"               : {"type": str, "required": True},
            "SubSegment"            : {"type": str, "required": True},
            "UnitVariantStandar"    : {"type": str, "required": False},
            "IsRegionMapping"       : {"type": str, "required": True},
            "CatalogueStatus"       : {"type": str, "required": False},
        }
    }
}