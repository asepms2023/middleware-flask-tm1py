# =========================
# IMPORTS
# =========================
import os
import logging
from datetime import datetime
from Utils.normalizer import normalize
from Services.base_service import (
    write_csv,
    build_error_row,
    get_source_file_location,
    run_ti_process,
    move_processed_file,
)

# =========================
# CONSTANTS
# =========================
vCSV_HEADERS = [
    "SyncCode",
    "MainDealerCode",
    "CutoffDate",
    "CutoffTime",
    "Material",
    "MaterialDescription",
    "ColorCode",
    "ColorDescription",
    "CommercialName",
    "TypeColor",
    "Series",
    "Segment",
    "SubSegment",
    "UnitVariantStandar",
    "IsRegionMapping",
    "CatalogueStatus",
    "Status",
    "Message",
    "Date",
    "Time"
]

vLog = logging.getLogger("app")


# =========================
# WRITE ERROR CSV
# =========================
def write_error_csv(vSync, vMessage):
    vPath = os.path.join(get_source_file_location(), "MasterData_Catalogue.csv")
    vRows = build_error_row(vSync, vMessage, vCSV_HEADERS)
    write_csv(vPath, vCSV_HEADERS, vRows)


# =========================
# PROCESS DATA
# =========================
def process_data(vData):
    vPath = os.path.join(get_source_file_location(), "MasterData_Catalogue.csv")
    vData = normalize("UMCM", vData)

    vSync       = vData.get("SyncCode", "")
    vCutoffDate = vData.get("CutoffDate", "")
    vCutoffTime = vData.get("CutoffTime", "")
    vNow        = datetime.now()
    vDate       = vNow.strftime("%Y-%m-%d")
    vTime       = vNow.strftime("%H:%M:%S")

    vRows = []

    for vMain in vData.get("MainDealers", []):
        vMainDealerCode = vMain.get("MainDealerCode", "")

        for vUnit in vMain.get("UnitTypes", []):
            vCommercialName = vUnit.get("CommercialName", "")
            vColorCode      = vUnit.get("ColorCode", "")
            vType_Color     = f"{vCommercialName} {vColorCode}".strip()

            vRows.append({
                "SyncCode"           : vSync,
                "MainDealerCode"     : vMainDealerCode,
                "CutoffDate"         : vCutoffDate,
                "CutoffTime"         : vCutoffTime,
                "Material"           : vUnit.get("Material", ""),
                "MaterialDescription": vUnit.get("Material Description", ""),
                "ColorCode"          : vColorCode,
                "ColorDescription"   : vUnit.get("ColorDescription", ""),
                "CommercialName"     : vCommercialName,
                "TypeColor"          : vType_Color,
                "Series"             : vUnit.get("Series", ""),
                "Segment"            : vUnit.get("Segment", ""),
                "SubSegment"         : vUnit.get("SubSegment", ""),
                "UnitVariantStandar" : vUnit.get("UnitVariantStandar", ""),
                "IsRegionMapping"    : vUnit.get("IsRegionMapping", ""),
                "CatalogueStatus"    : vUnit.get("CatalogueStatus", ""),
                "Status"             : 1,
                "Message"            : "Success",
                "Date"               : vDate,
                "Time"               : vTime
            })

    try:
        write_csv(vPath, vCSV_HEADERS, vRows)
    except Exception as vError:
        vLog.error(f"[{vSync}] CSV error: {vError}")
        raise RuntimeError("Internal Server Error")

    # =========================
    # RUN TI PROCESS
    # =========================
    try:
        run_ti_process("LoadData-01-MappingCatalogue")
    except RuntimeError:
        raise

    # =========================
    # MOVE FILE SETELAH TI SUKSES
    # =========================
    move_processed_file(vPath)