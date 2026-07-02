// Deterministic OpenSCAD smoke artifact for representation experiments.
$fn = 32;
difference() {
  cube([40, 20, 8], center=true);
  translate([-12, 0, 0]) cylinder(h=10, d=4, center=true);
  translate([12, 0, 0]) cylinder(h=10, d=4, center=true);
}
