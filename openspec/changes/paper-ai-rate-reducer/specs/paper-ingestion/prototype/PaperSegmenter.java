import java.util.ArrayList;
import java.util.List;

/**
 * paper-ingestion 结构化分段逻辑原型（仅验证 spec 中「论文结构化分段」与前置校验的行为）。
 * 只处理纯文本 / Markdown；未实现真实 docx / pdf 解析。
 */
public class PaperSegmenter {

    /** 单次处理长度上限（原型常量，真实实现应由配置提供）。 */
    public static final int MAX_LENGTH = 100000;

    /** 解析/分段失败。code 用于区分场景，供上层映射为提示文案。 */
    public static class IngestException extends RuntimeException {
        public final String code;

        public IngestException(String code, String message) {
            super(message);
            this.code = code;
        }
    }

    /** 一个段落单元。level=0 表示无章节标题的顶层段落。 */
    public static class Segment {
        public final int order;
        public final int level;
        public final String title;
        public final String content;

        public Segment(int order, int level, String title, String content) {
            this.order = order;
            this.level = level;
            this.title = title;
            this.content = content;
        }

        @Override
        public String toString() {
            return String.format("[#%d L%d 章节=%s] %s", order, level,
                    title == null ? "(无)" : title, content);
        }
    }

    public static List<Segment> segment(String rawText) {
        if (rawText == null || rawText.trim().isEmpty()) {
            throw new IngestException("EMPTY", "未识别到有效文本");
        }
        if (rawText.length() > MAX_LENGTH) {
            throw new IngestException("TOO_LONG",
                    "长度超限：单次处理上限 " + MAX_LENGTH + " 字符，当前 " + rawText.length());
        }

        List<Segment> segments = new ArrayList<>();
        int order = 0;
        int curLevel = 0;
        String curTitle = null;

        for (String block : rawText.split("\\r?\\n\\s*\\r?\\n")) {
            String text = block.trim();
            if (text.isEmpty()) {
                continue;
            }
            int level = headingLevel(text);
            if (level > 0) {
                curLevel = level;
                curTitle = text.replaceFirst("^#{1,6}\\s*", "").trim();
                segments.add(new Segment(order++, curLevel, curTitle, curTitle));
            } else {
                segments.add(new Segment(order++, curLevel, curTitle, text));
            }
        }

        if (segments.isEmpty()) {
            throw new IngestException("EMPTY", "未识别到有效文本");
        }
        return segments;
    }

    /** 返回 1..6 表示 Markdown 标题层级，0 表示普通段落。 */
    private static int headingLevel(String text) {
        int n = 0;
        while (n < text.length() && n < 6 && text.charAt(n) == '#') {
            n++;
        }
        if (n == 0) {
            return 0;
        }
        // '#' 后必须紧跟空格或结束，才算标题
        if (n < text.length() && text.charAt(n) != ' ') {
            return 0;
        }
        return n;
    }
}
