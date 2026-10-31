@echo off
rem v044 safe entry: diagnostics only; never auto bitgen or program hardware.
echo v044 SDRAM BIST diagnostic package. No release bitstream in this package.
echo From package root run:
echo python 01_project\tools\run_bist_diagnostic.py --td-bin "C:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin" --out "C:\FPGA_work\v044_td_new" --timeout 360
echo Output directory must be NEW. See 01_project\README.md and 00_*.md.
echo No compilation, bitgen or programming has been started by this BAT.
exit /b 0
