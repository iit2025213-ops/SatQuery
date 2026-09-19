const FOV = 38, R = 1;
const tanHalf = Math.tan(FOV / 2 * Math.PI / 180);
var c = 0.4000;
var psi = -1.5708;
var f_a = Math.atan(c * tanHalf);
var ta = Math.tan(f_a);
var vx = Math.cos(psi) * ta;
var vy = Math.sin(psi) * ta;
console.log("vx:", vx, "vy:", vy);
