param([string]$Python,[string]$PdfToPpm)
$ErrorActionPreference='Stop'
$r=Split-Path -Parent $PSScriptRoot
if(-not $Python){$bundled='C:\Users\33938\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe';if(Test-Path -LiteralPath $bundled){$Python=$bundled}else{$Python=(Get-Command python -ErrorAction Stop).Source}}
if(-not $PdfToPpm){$bundledPdf='C:\Users\33938\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe';if(Test-Path -LiteralPath $bundledPdf){$PdfToPpm=$bundledPdf}}
$path=Join-Path $r '01_docx\基于FPGA的多媒体广告牌_设计文档_V132_r04.docx'
$pdf=Join-Path $r '02_pdf\基于FPGA的多媒体广告牌_设计文档_V132_r04.pdf'
$w=$null;$d=$null
try {
 $w=New-Object -ComObject Word.Application
 $w.Visible=$false;$w.DisplayAlerts=0
 $d=$w.Documents.Open($path,$false,$false)
 $d.Fields.Update()|Out-Null
 foreach($toc in $d.TablesOfContents){$toc.Update();$toc.Range.Font.NameFarEast='宋体';$toc.Range.Font.Name='Times New Roman';$toc.Range.Font.Size=10;$toc.Range.ParagraphFormat.SpaceBefore=0;$toc.Range.ParagraphFormat.SpaceAfter=0;$toc.Range.ParagraphFormat.LineSpacingRule=4;$toc.Range.ParagraphFormat.LineSpacing=12;$toc.Range.ParagraphFormat.DisableLineHeightGrid=$true}
 $d.Repaginate()
 foreach($toc in $d.TablesOfContents){$toc.UpdatePageNumbers()}
 $d.Save()
 $d.ExportAsFixedFormat($pdf,17)
 $info=@{pages=$d.ComputeStatistics(2);words=$d.ComputeStatistics(0);toc_count=$d.TablesOfContents.Count;fields=$d.Fields.Count;renderer='Microsoft Word';docx=$path;pdf=$pdf}
 $info|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $r '03_review\word_render.json') -Encoding UTF8
 $info|ConvertTo-Json
} finally {
 if($d -ne $null){$d.Close(0);[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($d)}
 if($w -ne $null){$w.Quit();[void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($w)}
}
& $Python -X utf8 -B (Join-Path $r '04_tools\sanitize_metadata.py')
if($PdfToPpm){& $PdfToPpm -scale-to 1300 -png $pdf (Join-Path $r '03_review\page')}else{Write-Output 'PDF exported; optional PNG preview skipped. Pass -PdfToPpm to enable it.'}
