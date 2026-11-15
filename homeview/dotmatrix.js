// Dot-matrix renderer, injected by build_dashboard.py wherever a template in
// base.yaml contains the marker  /*DOTMATRIX*/ .  Defines  dm(text, options)
// which returns an inline SVG of 5x7 dot glyphs (digits, : ° % - and space).
// Plain ES2017 so it runs on Safari 15 (iPad Air 2).
// Section label: red dot + spaced capitals, optional right-hand text.
const ACCENT = '__ACCENT__';
const lbl = (t, right) =>
  '<div style="display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:.22em;opacity:.75;white-space:nowrap;">' +
  '<span style="flex:none;width:7px;height:7px;border-radius:50%;background:' + ACCENT + ';"></span>' +
  '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;">' + t + '</span>' +
  (right ? '<span style="flex:none;">' + right + '</span>' : '') + '</div>';

const dm = (text, opt) => {
  const o = Object.assign({ pitch: 10, dot: 0.74, on: '#F2F2F2', off: null, accent: ACCENT }, opt || {});
  const G = {
    '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    '3': ['11110', '00001', '00001', '01110', '00001', '00001', '11110'],
    '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
    '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
    '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
    '-': ['000', '000', '000', '111', '000', '000', '000'],
    ':': ['0', '0', '1', '0', '1', '0', '0'],
    '°': ['010', '101', '010', '000', '000', '000', '000'],
    '%': ['11001', '11010', '00010', '00100', '01000', '01011', '10011'],
    ' ': ['00', '00', '00', '00', '00', '00', '00'],
  };
  const chars = String(text).split('');
  const P = o.pitch;
  const R = ((P * o.dot) / 2).toFixed(2);
  let x = 0;
  let dots = '';
  chars.forEach((ch) => {
    const g = G[ch] || G[' '];
    const colour = ch === ':' ? o.accent : o.on;
    for (let r = 0; r < 7; r++) {
      for (let c = 0; c < g[r].length; c++) {
        const lit = g[r][c] === '1';
        if (!lit && !o.off) continue;
        dots += '<circle cx="' + ((x + c) * P + P / 2).toFixed(1) + '" cy="' + (r * P + P / 2).toFixed(1) +
                '" r="' + R + '" fill="' + (lit ? colour : o.off) + '"/>';
      }
    }
    x += g[0].length + 1;
  });
  const w = Math.max(0, x - 1) * P;
  return '<svg width="' + w + '" height="' + 7 * P + '" viewBox="0 0 ' + w + ' ' + 7 * P +
         '" style="display:block;overflow:visible">' + dots + '</svg>';
};
