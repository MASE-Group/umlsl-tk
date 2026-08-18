"""Named colour tables: plain data, no dependencies, no drawing.

A car's identity in this simulator *is* a colour name -- cars are called "Red",
"Teal", "Navy" -- so these tables are read by the car factory as well as by the
GUI. They live outside both for exactly that reason: neither owns them, and a
module that only wants to name a car should not have to import a GUI toolkit to
do it.

* `car_colors.selected_colors` -- the shortlist cars are named from, ordered so
  that the first few cars in a scenario get visually distinct colours.
* `color_names.colors` -- the full CSS-style table, used to keep naming cars
  once the shortlist runs out, and by the GUI for text and highlights.
"""
