import java.util.List;

/** PaperSegmenter 的 mock 数据测试入口，直接覆盖 spec 中的分段场景。 */
public class PaperSegmenterTest {

    private static int passed = 0;
    private static int failed = 0;

    public static void main(String[] args) {
        caseNormalSegmentation();
        caseEmptyContent();
        caseBlankOnly();
        caseTooLong();
        casePlainTextNoHeading();

        System.out.println();
        System.out.printf("结果: 通过 %d, 失败 %d%n", passed, failed);
        if (failed > 0) {
            System.exit(1);
        }
    }

    // 场景：正常分段 + 章节层次
    private static void caseNormalSegmentation() {
        String mock = "# 第一章 绪论\n\n"
                + "本文研究 AI 生成文本的识别问题。\n\n"
                + "## 1.1 研究背景\n\n"
                + "近年来大模型广泛用于学术写作。\n\n"
                + "自动生成内容带来了新的挑战。\n\n"
                + "# 第二章 方法\n\n"
                + "我们提出了一个分段检测方法。";

        List<PaperSegmenter.Segment> segs = PaperSegmenter.segment(mock);

        assertEquals("段落总数", 7, segs.size());
        assertEquals("第0段顺序", 0, segs.get(0).order);
        assertSegment("标题1", segs.get(0), 1, "第一章 绪论");
        assertSegment("标题1下正文", segs.get(1), 1, "第一章 绪论");
        assertSegment("子标题", segs.get(2), 2, "1.1 研究背景");
        assertSegment("子标题下正文", segs.get(3), 2, "1.1 研究背景");
        assertSegment("子标题下第二段仍归属", segs.get(4), 2, "1.1 研究背景");
        assertSegment("标题2", segs.get(5), 1, "第二章 方法");
        assertSegment("标题2下正文", segs.get(6), 1, "第二章 方法");
        assertTrue("正文内容正确", segs.get(4).content.equals("自动生成内容带来了新的挑战。"));
    }

    // 场景：空内容
    private static void caseEmptyContent() {
        expectError("空字符串", "", "EMPTY");
        expectError("null", null, "EMPTY");
    }

    // 场景：仅含空白
    private static void caseBlankOnly() {
        expectError("仅空白", "   \n\n  \t  ", "EMPTY");
    }

    // 场景：超长文档
    private static void caseTooLong() {
        StringBuilder sb = new StringBuilder();
        String line = "这是一行用于填充长度的论文内容。\n";
        while (sb.length() <= PaperSegmenter.MAX_LENGTH) {
            sb.append(line);
        }
        expectError("超长文档", sb.toString(), "TOO_LONG");
    }

    // 场景：纯文本无标题 -> 全部顶层
    private static void casePlainTextNoHeading() {
        String mock = "第一段内容。\n\n第二段内容。\n\n第三段内容。";
        List<PaperSegmenter.Segment> segs = PaperSegmenter.segment(mock);
        assertEquals("段落总数", 3, segs.size());
        for (PaperSegmenter.Segment s : segs) {
            assertEquals("层级为0", 0, s.level);
            assertTrue("无章节标题", s.title == null);
        }
        assertTrue("第2段内容", segs.get(1).content.equals("第二段内容。"));
    }

    // ---- 断言辅助 ----

    private static void assertSegment(String name, PaperSegmenter.Segment s, int level, String title) {
        assertEquals(name + " 层级", level, s.level);
        assertTrue(name + " 章节归属 (期望=" + title + ", 实际=" + s.title + ")",
                title.equals(s.title));
    }

    private static void assertTrue(String name, boolean cond) {
        if (cond) {
            pass(name);
        } else {
            fail(name, "期望 true");
        }
    }

    private static void assertEquals(String name, int expected, int actual) {
        if (expected == actual) {
            pass(name);
        } else {
            fail(name, "期望 " + expected + "，实际 " + actual);
        }
    }

    private static void expectError(String name, String input, String expectedCode) {
        try {
            PaperSegmenter.segment(input);
            fail(name, "期望抛出 " + expectedCode + "，但没有异常");
        } catch (PaperSegmenter.IngestException e) {
            if (expectedCode.equals(e.code)) {
                pass(name + " -> " + e.code + " / " + e.getMessage());
            } else {
                fail(name, "期望 " + expectedCode + "，实际 " + e.code);
            }
        }
    }

    private static void pass(String name) {
        passed++;
        System.out.println("  PASS  " + name);
    }

    private static void fail(String name, String detail) {
        failed++;
        System.out.println("  FAIL  " + name + " : " + detail);
    }
}
