/**
 * Tiny, safe renderer for the assistant's text (CONTRACT §9).
 *
 * It never produces HTML: ``parseSafeMarkdown`` returns plain data blocks and
 * the OWL template prints every string with ``t-esc``. Supported syntax:
 * **bold**, *italics*, bullet lists (- / * / •), numbered lists (1. / 1)),
 * simple pipe tables and line breaks. Everything else (links, images, HTML,
 * URLs) stays as literal text.
 *
 * Block shapes:
 *   {type: "p", inline: Segment[]}
 *   {type: "ul" | "ol", items: Segment[][]}
 *   {type: "table", header: Segment[][], rows: Segment[][][]}
 * Segment: {text, bold, italic} or {br: true}
 */

const MAX_TEXT = 20000;
const MAX_TABLE_COLUMNS = 12;

const BULLET_RE = /^\s*[-*•]\s+(.*)$/;
const ORDERED_RE = /^\s*\d{1,3}[.)]\s+(.*)$/;
const TABLE_SEPARATOR_RE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;
const INLINE_RE = /\*\*(?=\S)(.+?)(?<=\S)\*\*|\*(?=[^\s*])(.+?)(?<=[^\s*])\*/g;

/** @returns {{text: String, bold: Boolean, italic: Boolean}[]} */
export function parseInline(text, bold = false, italic = false) {
    const segments = [];
    let last = 0;
    const re = new RegExp(INLINE_RE.source, "g");
    let match = re.exec(text);
    while (match !== null) {
        if (match.index > last) {
            segments.push({text: text.slice(last, match.index), bold, italic});
        }
        if (match[1] !== undefined) {
            segments.push(...parseInline(match[1], true, italic));
        } else {
            segments.push(...parseInline(match[2], bold, true));
        }
        last = match.index + match[0].length;
        match = re.exec(text);
    }
    if (last < text.length) {
        segments.push({text: text.slice(last), bold, italic});
    }
    return segments;
}

function splitRow(line) {
    let row = line.trim();
    if (row.startsWith("|")) {
        row = row.slice(1);
    }
    if (row.endsWith("|")) {
        row = row.slice(0, -1);
    }
    return row
        .split("|")
        .slice(0, MAX_TABLE_COLUMNS)
        .map((cell) => parseInline(cell.trim()));
}

const isTableLine = (line) => line.trim().startsWith("|") && line.trim().length > 1;

/** @returns {Object[]} blocks */
export function parseSafeMarkdown(input) {
    const text = String(input ?? "")
        .replace(/\r\n?/g, "\n")
        .slice(0, MAX_TEXT);
    const lines = text.split("\n");
    const blocks = [];
    let paragraph = null;
    let list = null;
    const flush = () => {
        paragraph = null;
        list = null;
    };
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (!line.trim()) {
            flush();
            continue;
        }
        if (
            isTableLine(line) &&
            i + 1 < lines.length &&
            TABLE_SEPARATOR_RE.test(lines[i + 1])
        ) {
            flush();
            const table = {type: "table", header: splitRow(line), rows: []};
            i += 2;
            while (i < lines.length && isTableLine(lines[i])) {
                table.rows.push(splitRow(lines[i]));
                i++;
            }
            i--;
            blocks.push(table);
            continue;
        }
        let kind = null;
        let match = BULLET_RE.exec(line);
        if (match) {
            kind = "ul";
        } else {
            match = ORDERED_RE.exec(line);
            if (match) {
                kind = "ol";
            }
        }
        if (kind) {
            paragraph = null;
            if (!list || list.type !== kind) {
                list = {type: kind, items: []};
                blocks.push(list);
            }
            list.items.push(parseInline(match[1]));
            continue;
        }
        list = null;
        if (!paragraph) {
            paragraph = {type: "p", inline: []};
            blocks.push(paragraph);
        } else {
            paragraph.inline.push({br: true});
        }
        paragraph.inline.push(...parseInline(line.trim()));
    }
    return blocks;
}
