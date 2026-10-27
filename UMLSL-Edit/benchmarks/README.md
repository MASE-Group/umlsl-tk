# UMLSL-Edit benchmarks

The measurements behind the model-checker evaluation in the UMLSL-TK paper: how
long the model checker takes to decide a formula as the traffic in the ego
car's view grows, and how much that depends on where the cars are.

```bash
cd UMLSL-Edit/benchmarks
python formula_timing.py                          # the timing table, F1..F4
python formula_timing.py --formulas F5 F6         # its slow columns
python formula_timing.py --layouts random0 random1 random2 random3 random4 \
    random5 random6 random7 random8 random9       # the placement table
python summarise.py                               # the LaTeX rows for the timing table
python summarise.py --placement                   # ... and for the placement table
```

They import `umlsl_edit`, so run them in the environment `install.sh edit`
created. Results land in `results/` as JSON, holding every sample behind each
median together with the verdict, the cars in view and their placements. The
committed files are the run the paper quotes, made single-threaded on an
Apple M1 Max with Python 3.14 on an otherwise idle machine.

## The scenario

`scene.py` builds a grid of eight roads, four horizontal and four vertical,
60 units apart with two lanes per direction, holding 40 cars. The ego car E
drives on an inner road just before a crossing; with the editor's default
braking deceleration and maximum speed, its view is about 29 units long, spans
three virtual lanes and runs into the crossing.

The traffic in E's view is varied without changing the scenario: `k - 1` cars
are placed on E's road inside the view, the remaining `40 - k` are parked on
the outer roads, far outside it. A car is *in the view* when its reservation or
claim overlaps it, which is the set the model checker's quantifiers range over;
E counts. `uniform` spaces the `k - 1` cars evenly over the three lanes,
`random<i>` places them at random (seeded by `i` and `k`, so a layout is the
same on every run).

The snapshot is loaded with `TrafficSnapshotModel.from_dict`, the path the
editor's evaluation worker takes. A sample is what the editor does when a
formula is re-checked: parse it, then evaluate it over E's whole view.

## Placement and scenario size

The timing table uses the uniform layout. The placement table repeats F1..F4
over ten random placements per density and prints F3 and F4, the formulas a
placement can make false: a random placement can put a car right in front of E,
and then the checker has to exhaust its candidates. `summarise.py --spread`
prints the spread over placements for all four.

`--total-cars` puts the ten-car view in a scenario of 10 or 80 cars instead of
40:

```bash
python formula_timing.py --cars 10 --total-cars 10
python formula_timing.py --cars 10 --total-cars 80
python summarise.py --spread
```

The model checker carries only the cars with something in the view into it, so
these should match the timing table's ten-car row up to the cost of building
the view.

## The formulas

`l = k` is written `l >= k and l <= k`; the query language has no length
equality. F5 and F6 measure the chop depth. F5 has six chops, counting the
somewhere operator as one as the paper does: five left-nested chops over two
length constants, alternating, then `free`. It holds on a space 7 long, but
the checker tries candidates whose failure has to be established through all
five chops before it reaches it; `trace_witness.py F5` counts them. F6 has
three chops and a last operand that no space in the view satisfies, so there is
no witness and the checker has to exhaust its candidates.

F5 and F6 take up to minutes per sample, so they have a run of their own and,
where they are slow, only a few samples per density.

## Reproducibility

Placements are deterministic, so verdicts, cars in view and the work the
checker does are identical from run to run. Only the timings vary. Each
median is over 15 samples, or fewer where a formula takes long enough that the
`--budget` (60 s per formula and density by default) runs out first, but never
fewer than three; the samples are in the result files.

A single sample is capped at `--timeout`, 10 minutes by default. A formula
whose sample hits the cap is recorded as not terminating within it
(`"timed_out": true`, no verdict) and is not sampled again; `summarise.py`
prints it as `t/o`.
