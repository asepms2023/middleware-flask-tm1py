from Integrations.tm1_connection import get_tm1

with get_tm1() as tm1:
    vDf = tm1.cubes.cells.execute_mdx_dataframe("""
        SELECT
            {[MeasureControlPanel].[String],
              [MeasureControlPanel].[Numeric]} ON COLUMNS,
            {[ControlPanelAPIItem].Members} ON ROWS
        FROM [00-ControlPanelAPI]
    """)

print("COLUMNS:", vDf.columns.tolist())
print("INDEX:", vDf.index.tolist())
print(vDf.to_string())