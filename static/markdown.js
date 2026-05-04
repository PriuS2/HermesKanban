export function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function renderMarkdown(value = '') {
  let html = escapeHtml(value);
  html = html.replace(/^### (.*)$/gm, '<h4>$1</h4>')
             .replace(/^## (.*)$/gm, '<h3>$1</h3>')
             .replace(/^# (.*)$/gm, '<h2>$1</h2>')
             .replace(/`([^`]+)`/g, '<code>$1</code>')
             .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
             .replace(/
/g, '<br>');
  return html;
}
