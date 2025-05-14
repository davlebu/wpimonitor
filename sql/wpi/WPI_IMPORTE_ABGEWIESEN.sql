 SELECT [meldetermin]
          ,[melder_id_art]
          ,[melder_id]
          ,[import_anwendungs_id]
          ,[import_blz]
          ,[import_befoerderungs_datum]
          ,[import_externe_referenz]
          , CASE
    WHEN [import_gelesene_ACS_info_header] = 'NON_ACS' AND
         [import_datei_id] LIKE '[0-9]% - %'
    THEN SUBSTRING([import_datei_id], CHARINDEX(' - ', [import_datei_id]) + 3, LEN([import_datei_id]))
    ELSE [import_datei_id]
  END AS [import_datei_id]
          ,[import_empfangszeit]
          ,[import_dateiname]
          ,[abweisen_check_befund_check_name]
          ,[abweisen_check_befund_check_gruppe]
          ,[abweisen_check_befund_check_beschreibung_kurz]
          ,[abweisen_check_befund_check_beschreibung_extern]
          ,[abweisen_check_befund_check_details]
          ,[import_meldetermin]
          ,[import_melder_id_art]
          ,[import_melder_id]
      FROM [REPORTING].[dbo].[wpi-importe-abgewiesen-flat]
      WHERE coalesce(import_befoerderungs_datum,{IMPORT_CUT_DATE}) >= {IMPORT_CUT_DATE}