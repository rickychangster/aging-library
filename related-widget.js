(function () {
  var dataEl = document.getElementById('related-data');
  if (!dataEl) return;

  var data;
  try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
  if (!data.related || data.related.length === 0) return;

  // ── Styles ─────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = [
    '.rw{max-width:810px;margin:0 auto;padding:0 40px 80px}',
    '.rw-divider{border:none;border-top:1px solid #d8d3c8;margin-bottom:40px}',
    '.rw-heading{font-family:"Fragment Mono",monospace;font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#c17a1a;margin-bottom:22px}',
    '.rw-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-bottom:32px}',
    '.rw-card{display:block;background:#fff;border:1px solid #e8e4db;border-radius:6px;padding:18px 20px 16px;text-decoration:none;color:inherit;transition:border-color .15s,box-shadow .15s}',
    '.rw-card:hover{border-color:#c17a1a;box-shadow:0 2px 8px rgba(193,122,26,.1)}',
    '.rw-tags{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}',
    '.rw-tag{font-family:"Fragment Mono",monospace;font-size:9px;letter-spacing:.3px;padding:2px 7px;border-radius:100px;background:rgba(193,122,26,.1);color:#9a5f0e}',
    '.rw-title{font-family:"Newsreader",serif;font-size:16px;font-weight:700;line-height:1.25;color:#222;margin-bottom:4px}',
    '.rw-arr{font-family:"Fragment Mono",monospace;font-size:10.5px;color:#c17a1a;letter-spacing:.4px}',
    '.rw-back{font-family:"Fragment Mono",monospace;font-size:10px;letter-spacing:.8px;text-transform:uppercase}',
    '.rw-back a{color:#737068;text-decoration:none;border-bottom:1px solid #d8d3c8;padding-bottom:1px}',
    '.rw-back a:hover{color:#222;border-color:#222}',
    '@media(max-width:640px){.rw{padding:0 20px 60px}.rw-grid{grid-template-columns:1fr}}'
  ].join('');
  document.head.appendChild(style);

  // ── Markup ─────────────────────────────────────────
  var section = document.createElement('div');
  section.className = 'rw';

  var cardsHTML = data.related.map(function (r) {
    var tagsHTML = (r.tags || []).slice(0, 2).map(function (t) {
      return '<span class="rw-tag">' + escapeHTML(t) + '</span>';
    }).join('');

    return '<a href="' + escapeHTML(r.filename) + '" class="rw-card">' +
      (tagsHTML ? '<div class="rw-tags">' + tagsHTML + '</div>' : '') +
      '<div class="rw-title">' + escapeHTML(r.title) + '</div>' +
      '<div class="rw-arr">Read →</div>' +
      '</a>';
  }).join('');

  section.innerHTML =
    '<hr class="rw-divider">' +
    '<div class="rw-heading">Continue Reading</div>' +
    '<div class="rw-grid">' + cardsHTML + '</div>' +
    '<div class="rw-back"><a href="../index.html">← Back to Library</a></div>';

  document.body.appendChild(section);

  function escapeHTML(str) {
    return String(str)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
})();
