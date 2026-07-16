# from Integrations.tm1_connection import get_tm1

# with get_tm1() as tm1:
#     vDf = tm1.cubes.cells.execute_mdx_dataframe("""
#         SELECT
#             {[MeasureControlPanel].[String],
#               [MeasureControlPanel].[Numeric]} ON COLUMNS,
#             {[ControlPanelAPIItem].Members} ON ROWS
#         FROM [00-ControlPanelAPI]
#     """)

# print("COLUMNS:", vDf.columns.tolist())
# print("INDEX:", vDf.index.tolist())
# print(vDf.to_string())

from Integrations.tm1_connection import get_tm1

with get_tm1() as tm1:
    # 1. Cek apakah dimensi SyncCode ada, dan elemen UMCM ada di dalamnya
    sElements = tm1.elements.get_element_names("SyncCode", "SyncCode")
    print("ELEMENTS IN SyncCode DIMENSION:", list(sElements))

    # 2. Cek tanpa filter elemen -- ambil SEMUA baris cube attribute
    #    (tanpa suppress) supaya kelihatan yang terisi maupun kosong
    vDf = tm1.cubes.cells.execute_mdx_dataframe("""
        SELECT
            NON EMPTY {[}ElementAttributes_SyncCode].[FileNamePrefix]} ON COLUMNS,
            {[SyncCode].[SyncCode].Members} ON ROWS
        FROM [}ElementAttributes_SyncCode]
    """)
    print("COLUMNS:", vDf.columns.tolist())
    print(vDf.to_string())