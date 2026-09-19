const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, 'public/globe.html');
let content = fs.readFileSync(file, 'utf8');

const newKeys = `  var KEYS = [
    { s: 0.0, c:  0.4000, psi: -1.5708, r: 0.85, rx:  0.10, ry: -1.20, l: [-0.30,  0.32, 0.89] },
    { s: 0.1, c:  0.4000, psi: -1.5708, r: 0.85, rx:  0.10, ry: -1.05, l: [-0.30,  0.32, 0.89] },
    { s: 0.8, c:  0.6000, psi: -1.5708, r: 1.00, rx:  0.05, ry: -0.30, l: [-0.26,  0.26, 0.93] },
    { s: 1.6, c:  0.8000, psi: -1.5708, r: 1.30, rx:  0.14, ry: -0.45, l: [-0.34,  0.34, 0.88] },
    { s: 2.6, c:  1.4000, psi: -1.5708, r: 2.00, rx:  0.55, ry: -1.10, l: [-0.36,  0.58, 0.73] },
    { s: 3.2, c:  1.8000, psi: -1.5708, r: 2.50, rx:  0.78, ry: -1.45, l: [-0.38,  0.66, 0.65] },
    { s: 3.8, c:  1.5000, psi: -1.5708, r: 2.20, rx:  0.55, ry: -1.50, l: [-0.55,  0.52, 0.65] },
    { s: 4.8, c:  1.2000, psi: -1.5708, r: 1.80, rx:  0.05, ry: -1.25, l: [-0.84,  0.26, 0.47] },
    { s: 5.4, c:  0.9000, psi: -1.5708, r: 1.50, rx: -0.12, ry: -1.10, l: [-0.90,  0.20, 0.39] },
    { s: 6.0, c:  1.1000, psi: -1.5708, r: 1.70, rx: -0.30, ry: -0.95, l: [-0.80,  0.02, 0.60] },
    { s: 7.0, c:  1.3000, psi: -1.5708, r: 2.00, rx: -0.52, ry: -0.72, l: [-0.55, -0.42, 0.72] }
  ];`;

content = content.replace(/var KEYS = \[\s*\{ s: 0\.0[\s\S]*?\];/, newKeys);
fs.writeFileSync(file, content);
console.log('Replaced KEYS array');
