const FOV = 38, R = 1;
const tanHalf = Math.tan(FOV / 2 * Math.PI / 180);
var desiredR = 0.70;
var theta = Math.atan(desiredR * tanHalf);
var dist  = R / Math.sin(theta);
var yOff = -0.40 * tanHalf * dist;
console.log("dist:", dist);
console.log("yOff:", yOff);
