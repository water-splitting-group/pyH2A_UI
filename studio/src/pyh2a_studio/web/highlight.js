/* Syntax highlighting for a pyH2A input file.
 *
 * Not a markdown highlighter. These files are markdown only in the sense that they are
 * pipe tables under `#` headings; everything that matters about them — which cell is a
 * name, which is a magnitude, which is a unit, which is a live reference into another
 * table — is pyH2A's grammar, and a generic highlighter paints all of it one colour.
 *
 * So the header row is parsed first and the rest of the table is coloured by *column*:
 * a cell under `Cost_Unit` is a unit, a cell under `Comment` is prose, and a cell under
 * `Usage_Value` is a magnitude. That is the difference between decoration and being able
 * to see, in a 500-line file, that one row is missing its unit.
 *
 * Monokai, because the user asked for it and because the source drawer is the one place
 * in this app you are looking at the file as a file. The worksheet stays on paper.
 */

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;' };

function safe(text) {
  return text.replace(/[&<>]/g, (character) => ESCAPES[character]);
}

function span(kind, text) {
  return text ? `<span class="t-${kind}">${safe(text)}</span>` : '';
}

/* A cell's colour from its column heading. Anything unrecognised is left as a value,
 * which is right: an unknown column in a pyH2A file is usually still a number. */
function kindOfColumn(heading) {
  const name = (heading || '').trim();
  if (name === 'Name') return 'name';
  if (name === 'Comment' || name === 'Description') return 'comment';
  if (name === 'Unit' || name.endsWith('_Unit')) return 'unit';
  if (name === 'Path' || name.endsWith('_Path')) return 'path';
  return 'value';
}

const NUMBER = /^-?[\d,]+\.?\d*(?:[eE][-+]?\d+)?%?$/;

/* Inside a cell, three things override the column's colour, because they are visibly
 * different kinds of thing wherever they appear:
 *   {Table > Row > Value}   a live reference — the edges of the model
 *   pyH2A.Config~File.md    a path into the package
 *   None / -                the engine's two ways of writing "nothing here"
 */
function cell(text, columnKind) {
  const body = text.trim();
  if (!body) return safe(text);

  const lead = text.slice(0, text.length - text.trimStart().length);
  const tail = text.slice(text.trimEnd().length);
  let painted;

  if (body.startsWith('{') && body.endsWith('}')) {
    painted = span('ref', body);
  } else if (body.includes('~')) {
    painted = span('path', body);
  } else if (body === 'None' || body === '-') {
    painted = span('nil', body);
  } else if (columnKind === 'value' && NUMBER.test(body)) {
    painted = span('number', body);
  } else {
    painted = span(columnKind, body);
  }
  return lead + painted + tail;
}

function row(line, headings) {
  const parts = line.split('|');
  return parts
    .map((part, index) => cell(part, index === 0 ? 'name' : kindOfColumn(headings[index])))
    .join(span('pipe', '|'));
}

const HEADING = /^(#+)(\s+)(.*)$/;
const RULE = /^[\s|:-]+$/;

/**
 * One pyH2A input file as highlighted HTML, line for line.
 *
 * Line-for-line matters: this is painted underneath a transparent textarea, so every
 * line must occupy exactly the height of the line it is standing in for. Nothing here
 * wraps, collapses or reflows.
 */
export function highlight(markdown) {
  const lines = String(markdown ?? '').split('\n');
  const out = [];
  let headings = [];
  let expectingHeader = false;

  for (const line of lines) {
    const heading = HEADING.exec(line);
    if (heading) {
      // A new table starts here, so the columns of the last one no longer apply.
      headings = [];
      expectingHeader = true;
      out.push(span('hash', heading[1]) + heading[2] + span('heading', heading[3]));
      continue;
    }

    if (!line.trim()) { out.push(''); continue; }

    if (!line.includes('|')) {
      // Prose outside a table. pyH2A ignores it, and so should the eye.
      out.push(span('loose', line));
      continue;
    }

    if (RULE.test(line)) {
      out.push(span('rule', line));
      continue;
    }

    if (expectingHeader) {
      headings = line.split('|').map((part) => part.trim());
      expectingHeader = false;
      out.push(line.split('|').map((part) => span('column', part)).join(span('pipe', '|')));
      continue;
    }

    out.push(row(line, headings));
  }

  // A trailing newline must still occupy a line, or the last line drifts out of register
  // with the textarea behind it.
  return out.join('\n') + '\n';
}
