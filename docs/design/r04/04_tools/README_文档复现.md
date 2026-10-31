# 文档复现

先自行安装Microsoft Word、Python与requirements_document.txt中的库；PNG缩略图为可选Poppler工具。

保持00_source、01_docx、02_pdf、03_review、04_tools、05_github的相对结构：

1. `python -B 04_tools/build_revision.py`：从原DOCX生成修订稿。
2. `powershell -File 04_tools/render_word.ps1 -Python "本机python.exe完整路径" -PdfToPpm "本机pdftoppm.exe完整路径"`：更新目录、SEQ/REF与页码，导出PDF并清除自动作者属性。
3. `python -B 04_tools/quality_check.py`：核对版面参数、引用、原图/公式、匿名化、分页与内容指纹。

Word版本和字体环境可能造成重新分页。未验证GitHub上传时保留05_github/publish_status.json的false状态；不要手工改成已发布来伪造提交。

这些工具只处理文档，不操作网络、板卡、TF或Flash。请在工作副本中运行，禁止修改冻结归档快照。
