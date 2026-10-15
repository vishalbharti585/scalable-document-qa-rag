import re

class MarkdownRendererPy:
    @staticmethod
    def escape_html(text):
        if not text:
            return ""
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

    @classmethod
    def render_inline(cls, text):
        if not text:
            return ""
        # Inline code
        text = re.sub(r"`([^`\n]+)`", r'<code class="inline-code">\1</code>', text)
        # Bold & Italic
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
        text = re.sub(r"___(.+?)___", r"<strong><em>\1</em></strong>", text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
        # Strikethrough
        text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
        # Italic
        text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?!\s)\*(?!\*)", r"<em>\1</em>", text)
        text = re.sub(r"(?<!_)_(?!\s)(.+?)(?!\s)_(?!_)", r"<em>\1</em>", text)
        return text

    @classmethod
    def render(cls, md):
        if not md:
            return ""
        text = md.replace("\r\n", "\n").replace("\r", "\n")
        text = cls.escape_html(text)

        # 1. Code blocks
        code_blocks = []
        def repl_code(m):
            idx = len(code_blocks)
            lang = m.group(1)
            code = m.group(2).strip()
            lang_label = f'<div class="code-lang">{lang}</div>' if lang else ""
            code_blocks.append(f'<div class="code-block-wrapper">{lang_label}<pre class="code-block"><code>{code}</code></pre></div>')
            return f"\n\n@@CODEBLOCK_{idx}@@\n\n"
        text = re.sub(r"```([a-zA-Z0-9_\-]*)\n([\s\S]*?)```", repl_code, text)

        # 2. Tables
        tables = []
        def repl_table(m):
            idx = len(tables)
            headers = [c.strip() for c in m.group(1).split("|")[1:-1]]
            rows = [[c.strip() for c in r.split("|")[1:-1]] for r in m.group(3).strip().split("\n")]
            html = '<div class="table-responsive"><table class="markdown-table"><thead><tr>'
            for h in headers:
                html += f"<th>{cls.render_inline(h)}</th>"
            html += "</tr></thead><tbody>"
            for row in rows:
                html += "<tr>"
                for cell in row:
                    html += f"<td>{cls.render_inline(cell)}</td>"
                html += "</tr>"
            html += "</tbody></table></div>"
            tables.append(html)
            return f"\n\n@@TABLE_{idx}@@\n\n"
        text = re.sub(r"(?:^|\n)(\|(?:[^\n]+\|)+)\n(\|(?:[\s\-:]+\|)+)\n((?:\|(?:[^\n]+\|)+(?:\n|$))+)", repl_table, text)

        # 3. Block parser line-by-line
        lines = text.split("\n")
        output = []
        list_stack = [] # [{'type': 'ul'|'ol', 'indent': int}]
        para_lines = []

        def flush_para():
            nonlocal para_lines
            if para_lines:
                p_text = "<br>".join(para_lines)
                output.append(f'<p class="md-p">{cls.render_inline(p_text)}</p>')
                para_lines = []

        def close_lists_down_to(target_indent=None, target_type=None):
            nonlocal list_stack
            while list_stack:
                top = list_stack[-1]
                if target_indent is not None and top["indent"] < target_indent:
                    break
                if target_indent is not None and top["indent"] == target_indent and (target_type is None or top["type"] == target_type):
                    break
                popped = list_stack.pop()
                tag = popped["type"]
                output.append(f"</li></{tag}>")
            if list_stack and target_indent is not None and list_stack[-1]["indent"] == target_indent:
                output.append("</li>")

        def close_all_lists():
            close_lists_down_to(-1)

        list_regex = re.compile(r"^(\s*)(?:([\*\-\+])|(\d+)\.)\s+(.*)$")
        heading_regex = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$")
        hr_regex = re.compile(r"^(?:---|\*\*\*|___)\s*$")
        blockquote_regex = re.compile(r"^>\s?(.*)$")

        i = 0
        while i < len(lines):
            line = lines[i]
            trimmed = line.strip()

            # Empty line
            if not trimmed:
                flush_para()
                close_all_lists()
                i += 1
                continue

            # Codeblock placeholder
            m_cb = re.match(r"^@@CODEBLOCK_(\d+)@@$", trimmed)
            if m_cb:
                flush_para()
                close_all_lists()
                output.append(code_blocks[int(m_cb.group(1))])
                i += 1
                continue

            # Table placeholder
            m_tbl = re.match(r"^@@TABLE_(\d+)@@$", trimmed)
            if m_tbl:
                flush_para()
                close_all_lists()
                output.append(tables[int(m_tbl.group(1))])
                i += 1
                continue

            # Heading
            m_h = heading_regex.match(trimmed)
            if m_h:
                flush_para()
                close_all_lists()
                lvl = len(m_h.group(1))
                h_text = cls.render_inline(m_h.group(2).strip())
                output.append(f'<h{lvl} class="md-h{lvl}">{h_text}</h{lvl}>')
                i += 1
                continue

            # HR
            if hr_regex.match(trimmed):
                flush_para()
                close_all_lists()
                output.append('<hr class="md-hr">')
                i += 1
                continue

            # Blockquote
            m_bq = blockquote_regex.match(trimmed)
            if m_bq:
                flush_para()
                close_all_lists()
                bq_lines = [m_bq.group(1)]
                while i + 1 < len(lines):
                    next_bq = blockquote_regex.match(lines[i+1].strip())
                    if next_bq:
                        bq_lines.append(next_bq.group(1))
                        i += 1
                    else:
                        break
                bq_html = "<br>".join(cls.render_inline(l) for l in bq_lines)
                output.append(f'<blockquote class="md-blockquote">{bq_html}</blockquote>')
                i += 1
                continue

            # List Item
            m_li = list_regex.match(line)
            if m_li:
                flush_para()
                raw_indent = len(m_li.group(1).replace("\t", "    "))
                bullet_char = m_li.group(2)
                l_type = "ul" if bullet_char else "ol"
                li_content = cls.render_inline(m_li.group(4))
                li_class = "md-li" if l_type == "ul" else "md-li-ordered"

                if not list_stack:
                    list_stack.append({"type": l_type, "indent": raw_indent})
                    output.append(f'<{l_type} class="md-{l_type}"><li class="{li_class}">{li_content}')
                elif raw_indent > list_stack[-1]["indent"]:
                    list_stack.append({"type": l_type, "indent": raw_indent})
                    nested_cls = f"md-{l_type} md-{l_type}-nested"
                    output.append(f'<{l_type} class="{nested_cls}"><li class="{li_class}">{li_content}')
                else:
                    close_lists_down_to(raw_indent, l_type)
                    if list_stack and list_stack[-1]["indent"] == raw_indent and list_stack[-1]["type"] == l_type:
                        output.append(f'<li class="{li_class}">{li_content}')
                    else:
                        list_stack.append({"type": l_type, "indent": raw_indent})
                        output.append(f'<{l_type} class="md-{l_type}"><li class="{li_class}">{li_content}')
                i += 1
                continue

            # If inside a list and indented continuation line
            if list_stack and (len(line) - len(line.lstrip())) > list_stack[-1]["indent"]:
                output.append(f"<br>{cls.render_inline(trimmed)}")
                i += 1
                continue

            # Plain paragraph text
            close_all_lists()
            para_lines.append(trimmed)
            i += 1

        flush_para()
        close_all_lists()
        return "\n".join(output)

test_input = """### Solar PV Deployments

Solar systems can be installed across various environments:

1. Structural Mounts:
   * Rooftops
   * Open land
   * Floating platforms
2. Off-grid Solutions:
   * Solar water pumps
   * Remote communications

### Classifications
* Horizontal Axis Wind Turbines (HAWT)
  * High efficiency
* Vertical Axis Wind Turbines (VAWT)
  * Omnidirectional
"""

if __name__ == "__main__":
    res = MarkdownRendererPy.render(test_input)
    print(res)
