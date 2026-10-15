/**
 * MarkdownRenderer - Safe, self-contained, indentation-aware Markdown parser for RAG Chat.
 * Supports: Nested ordered and unordered lists, H1-H6, GitHub tables, fenced code blocks with
 * language badges, inline code, bold/italic, blockquotes, horizontal rules, and paragraphs.
 * Sanitizes input first to guarantee zero XSS execution.
 */
class MarkdownRenderer {
  static escapeHtml(text) {
    if (!text) return "";
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  static renderInline(text) {
    if (!text) return "";
    // Inline code
    text = text.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');
    // Bold & Italic
    text = text.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
    text = text.replace(/___(.+?)___/g, "<strong><em>$1</em></strong>");
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/__(.+?)__/g, "<strong>$1</strong>");
    // Strikethrough
    text = text.replace(/~~(.+?)~~/g, "<del>$1</del>");
    // Italic (carefully ensuring no match on leading/trailing spaces)
    text = text.replace(/(?<!\*)\*(?!\s)(.+?)(?!\s)\*(?!\*)/g, "<em>$1</em>");
    text = text.replace(/(?<!_)_(?!\s)(.+?)(?!\s)_(?!_)/g, "<em>$1</em>");
    return text;
  }

  static render(markdown) {
    if (!markdown) return "";

    // 0. Normalize newlines and escape untrusted HTML
    let text = markdown.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    text = this.escapeHtml(text);

    // 1. Fenced Code Blocks (```lang ... ```)
    const codeBlocks = [];
    text = text.replace(/```([a-zA-Z0-9_\-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const idx = codeBlocks.length;
      const langLabel = lang ? `<div class="code-lang">${lang}</div>` : "";
      codeBlocks.push(
        `<div class="code-block-wrapper">${langLabel}<pre class="code-block"><code>${code.trim()}</code></pre></div>`
      );
      return `\n\n@@CODEBLOCK_${idx}@@\n\n`;
    });

    // 2. Tables (| Header | Header | ... | --- | --- | ... | Cell | Cell |)
    const tables = [];
    text = text.replace(/(?:^|\n)(\|(?:[^\n]+\|)+)\n(\|(?:[\s\-:]+\|)+)\n((?:\|(?:[^\n]+\|)+(?:\n|$))+)/g, (match, headerLine, alignLine, bodyLines) => {
      const idx = tables.length;
      const parseCells = (row) => row.split("|").slice(1, -1).map(c => c.trim());
      const headers = parseCells(headerLine);
      const rows = bodyLines.trim().split("\n").map(r => parseCells(r));

      let tableHtml = '<div class="table-responsive"><table class="markdown-table"><thead><tr>';
      headers.forEach(h => {
        tableHtml += `<th>${this.renderInline(h)}</th>`;
      });
      tableHtml += "</tr></thead><tbody>";
      rows.forEach(r => {
        tableHtml += "<tr>";
        r.forEach(cell => {
          tableHtml += `<td>${this.renderInline(cell)}</td>`;
        });
        tableHtml += "</tr>";
      });
      tableHtml += "</tbody></table></div>";
      tables.push(tableHtml);
      return `\n\n@@TABLE_${idx}@@\n\n`;
    });

    // 3. Block parser line-by-line
    const lines = text.split("\n");
    const output = [];
    const listStack = []; // [{ type: 'ul' | 'ol', indent: number }]
    let paraLines = [];

    const flushPara = () => {
      if (paraLines.length > 0) {
        const pText = paraLines.join("<br>");
        output.push(`<p class="md-p">${this.renderInline(pText)}</p>`);
        paraLines = [];
      }
    };

    const closeListsDownTo = (targetIndent = null, targetType = null) => {
      while (listStack.length > 0) {
        const top = listStack[listStack.length - 1];
        if (targetIndent !== null && top.indent < targetIndent) {
          break;
        }
        if (targetIndent !== null && top.indent === targetIndent && (targetType === null || top.type === targetType)) {
          break;
        }
        const popped = listStack.pop();
        output.push(`</li></${popped.type}>`);
      }
      if (listStack.length > 0 && targetIndent !== null && listStack[listStack.length - 1].indent === targetIndent) {
        output.push("</li>");
      }
    };

    const closeAllLists = () => {
      closeListsDownTo(-1);
    };

    const listRegex = /^(\s*)(?:([\*\-\+])|(\d+)\.)\s+(.*)$/;
    const headingRegex = /^(#{1,6})\s+(.+?)(?:\s+#+)?$/;
    const hrRegex = /^(?:---|\*\*\*|___)\s*$/;
    const blockquoteRegex = /^(?:>|&gt;)\s?(.*)$/;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Empty line -> boundaries between blocks
      if (!trimmed) {
        flushPara();
        closeAllLists();
        continue;
      }

      // Code block placeholder
      const cbMatch = trimmed.match(/^@@CODEBLOCK_(\d+)@@$/);
      if (cbMatch) {
        flushPara();
        closeAllLists();
        output.push(codeBlocks[parseInt(cbMatch[1], 10)]);
        continue;
      }

      // Table placeholder
      const tblMatch = trimmed.match(/^@@TABLE_(\d+)@@$/);
      if (tblMatch) {
        flushPara();
        closeAllLists();
        output.push(tables[parseInt(tblMatch[1], 10)]);
        continue;
      }

      // Heading (H1 through H6)
      const hMatch = trimmed.match(headingRegex);
      if (hMatch) {
        flushPara();
        closeAllLists();
        const level = hMatch[1].length;
        const hText = this.renderInline(hMatch[2].trim());
        output.push(`<h${level} class="md-h${level}">${hText}</h${level}>`);
        continue;
      }

      // Horizontal Rule
      if (hrRegex.test(trimmed)) {
        flushPara();
        closeAllLists();
        output.push('<hr class="md-hr">');
        continue;
      }

      // Blockquote
      const bqMatch = trimmed.match(blockquoteRegex);
      if (bqMatch) {
        flushPara();
        closeAllLists();
        const bqLines = [bqMatch[1]];
        while (i + 1 < lines.length && blockquoteRegex.test(lines[i + 1].trim())) {
          bqLines.push(lines[i + 1].trim().replace(/^(?:>|&gt;)\s?/, ""));
          i++;
        }
        const bqHtml = bqLines.map(l => this.renderInline(l)).join("<br>");
        output.push(`<blockquote class="md-blockquote">${bqHtml}</blockquote>`);
        continue;
      }

      // List Item (ordered or unordered, nested with arbitrary indentation)
      const liMatch = line.match(listRegex);
      if (liMatch) {
        flushPara();
        const rawIndent = liMatch[1].replace(/\t/g, "    ").length;
        const isUnordered = !!liMatch[2];
        const lType = isUnordered ? "ul" : "ol";
        const liContent = this.renderInline(liMatch[4]);
        const liClass = isUnordered ? "md-li" : "md-li-ordered";

        if (listStack.length === 0) {
          listStack.push({ type: lType, indent: rawIndent });
          output.push(`<${lType} class="md-${lType}"><li class="${liClass}">${liContent}`);
        } else if (rawIndent > listStack[listStack.length - 1].indent) {
          listStack.push({ type: lType, indent: rawIndent });
          const nestedCls = `md-${lType} md-${lType}-nested`;
          output.push(`<${lType} class="${nestedCls}"><li class="${liClass}">${liContent}`);
        } else {
          closeListsDownTo(rawIndent, lType);
          if (listStack.length > 0 && listStack[listStack.length - 1].indent === rawIndent && listStack[listStack.length - 1].type === lType) {
            output.push(`<li class="${liClass}">${liContent}`);
          } else {
            listStack.push({ type: lType, indent: rawIndent });
            output.push(`<${lType} class="md-${lType}"><li class="${liClass}">${liContent}`);
          }
        }
        continue;
      }

      // If currently inside a list and line is an indented continuation
      if (listStack.length > 0 && (line.length - line.trimStart().length) > listStack[listStack.length - 1].indent) {
        output.push(`<br>${this.renderInline(trimmed)}`);
        continue;
      }

      // Normal paragraph line
      closeAllLists();
      paraLines.push(trimmed);
    }

    flushPara();
    closeAllLists();

    return output.join("\n");
  }
}

if (typeof window !== "undefined") {
  window.MarkdownRenderer = MarkdownRenderer;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = MarkdownRenderer;
}
