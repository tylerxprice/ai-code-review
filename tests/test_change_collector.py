from ai_review.summarize.changes import ChangeCollector


def test_annotated_diff_line_numbers():
    diff = """diff --git a/file.txt b/file.txt
index 1111111..2222222 100644
--- a/file.txt
+++ b/file.txt
@@ -1,2 +1,3 @@
 line1
-line2
+line2 updated
+line3
"""
    collector = ChangeCollector(diff, annotate_line_numbers=True)
    annotated = collector.get_annotated_diff()

    assert " line1  (L1)" in annotated
    assert "-line2  (-L2)" in annotated
    assert "+line2 updated  (+L2)" in annotated
    assert "+line3  (+L3)" in annotated
