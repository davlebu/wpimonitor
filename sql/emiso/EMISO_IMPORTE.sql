SELECT
  [anwendungs_id],
  [blz],
  [befoerderungs_datum],
  [externe_referenz],
  CASE
    WHEN [gelesene_ACS_info_header] = 'NON_ACS' AND
         [datei_id] LIKE '[0-9]% - %'
    THEN SUBSTRING([datei_id], CHARINDEX(' - ', [datei_id]) + 3, LEN([datei_id]))
    ELSE [datei_id]
  END AS [datei_id],
  [empfangszeit],
  [dateiname],
  [meldetermin],
  [melder_id],
  [melder_id_art]
FROM [REPORTING].[dbo].[emiso-importe]
    WHERE coalesce(befoerderungs_datum,{IMPORT_CUT_DATE}) >= {IMPORT_CUT_DATE}