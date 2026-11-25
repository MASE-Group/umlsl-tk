---
title: "Edit, Check, Simulate and Train: A Toolkit for UMLSL"
info: |
  SBMF 2026, Rio de Janeiro, Brazil, 02.12.2026.
  Talk on UMLSL-TK: UMLSL-Edit and UMLSL-Sim.
theme: default
canvasWidth: 960
duration: 28.5min
aspectRatio: 16/9
transition: none
fonts:
  provider: none
  sans: Helvetica Neue
  serif: Helvetica Neue
  mono: Menlo
drawings:
  enabled: false
mdc: true
colorSchema: light
exportFilename: astra-umlsl-tk-sbmf2026
kit:
  shortauthor: Hamarneh et al.
  shorttitle: "Edit, Check, Simulate and Train: A Toolkit for UMLSL"
  shortdate: 02.12.2026
  groupname: MASE group, KASTEL, KIT
layout: title
heading: Edit, Check, Simulate and Train
subtitle: A Toolkit for Urban Multi-Lane Spatial Logic
authors: Qais Hamarneh, Nils Wenninghoff, Akhila Bairy, Mattis Bihler, Florian Portscher, Tim Kreuch, Tao Schmidt, Maike Schwammberger
event: SBMF 2026, Rio de Janeiro, Brazil
date: 02.12.2026
image: /shots/sim_two_scene.png
imagePosition: 38% center
---



<!--
[0:30 | total 0:30]

Welcome. This paper presents UMLSL-TK: two tools that make Urban Multi-Lane Spatial Logic executable. UMLSL-Edit constructs and checks a traffic snapshot. UMLSL-Sim explores how traffic and a learning agent behave over time. The connecting idea is that spatial safety can be both a property to check and a constraint on action.
Source: paper, title and abstract. Introduce the authors collectively; do not read the full list.
-->

---
section: Motivation
---

# Can we connect a safety claim to traffic?

<div class="question-pair">
  <div><span class="eyebrow">A traffic snapshot</span><b>Do reservations overlap?</b></div>
  <div><span class="eyebrow">A driving policy</span><b>Which actions remain safe?</b></div>
</div>
<div class="wide-diagram" style="width:740px"><ToolkitLoop /></div>
<div class="takeaway">Draw a situation. Decide a spatial property. Explore its evolution.</div>
<div class="source">Paper §§1–2, Fig. 1</div>

<!--
[1:00 | total 1:30]

Test drives show what happened in particular runs. They cannot by themselves prove safety. Formal methods give us a way to state what safety means, but a spatial specification is useful in practice only if we can evaluate it on concrete traffic.
Point to the two questions. The first concerns one snapshot; the second concerns choices as traffic evolves. Earlier UMLSL controller studies used abstract functions in UPPAAL. This paper enables direct formula checking on a drawn scene, then simulation and learning with the same traffic concepts.
Trace the loop, without presenting it as an agenda: the editor checks a scenario, the simulator explores behavior, and a snapshot returns for analysis. A checked starting state is not a proof of every future trajectory.
Transition: what exactly does a spatial safety claim describe?
-->

---
section: Background
---

# Safety is about reserved space

<div class="wide-diagram" style="width:680px"><MlslView /></div>
<div class="takeaway">Discrete lanes · continuous positions · a local view around ego <Tex e="E" /></div>
<div class="source">Paper §3; MLSL model of Hilscher et al. [20]</div>

<!--
[1:15 | total 2:45]

UMLSL extends the highway traffic model and the Multi-Lane Spatial Logic, MLSL, of Hilscher et al. So we start on the highway.

Each car reserves the space of its safety envelope. The envelope covers the size of the car, its stopping distance, and a buffer. With it, a car can always stop without hitting the car in front.

Before a lane change, a car first claims space on the adjacent lane. Here, C claims space on lane 1. The claim tells the other cars what C wants to do, like a turn signal.

Formulas are evaluated from the view of one car, the ego car E. The virtual view reaches a fixed horizon h backwards and forwards from E. The set of lanes in the view is discrete. The interval along the lanes is continuous. Car A is outside the view, so formulas for E do not see it.

Transition: now we need a language for describing pieces of this view.
-->

---

# Describe space by splitting the view

<div class="wide-diagram" style="width:690px"><ChopDiagram /></div>
<div class="definition-strip"><span><Tex e="\mathit{re}(C)" /> reserved</span><span><Tex e="\mathit{cl}(C)" /> claimed</span><span><Tex e="\ell > k" /> length</span><span><Tex e="\langle\varphi\rangle" /> somewhere</span></div>
<div class="takeaway"><Tex e="\mathit{safe}\equiv\neg\exists c\colon c\ne E\land\langle\mathit{re}(c)\land\mathit{re}(E)\rangle" /></div>
<div class="source">Paper §3.2, Def. 3.3</div>

<!--
[1:30 | total 4:15]

Start with the rectangle as the observed space, initially the whole view. Point to horizontal chop: there must be a split point r with the first formula true on the left and the second on the right. Then point to vertical chop: split the lane sequence at a lane border. The subformulas are evaluated on the resulting spaces.
The atoms say a single lane space is reserved or claimed by a car; a length comparison constrains its continuous extent. Somewhere means that a formula holds on some subspace, built from chops. We need not expand that definition on screen.
Read the safety formula from inside out. Could another car and E reserve the same positive-length subspace? Safety says no. Boundary contact alone is not overlap under the paper's convention.
Transition: this spatial question can guard a controller's next move.
-->

---
clicks: 2
---

# A claim makes the manoeuvre visible

<ClaimFlow :step="$clicks" />
<div class="takeaway"><Tex e="\mathit{pc}(E)\equiv\exists c\colon c\ne E\land\langle\mathit{cl}(E)\land(\mathit{re}(c)\lor\mathit{cl}(c))\rangle" /></div>
<div class="definition-strip"><span>Claim = intention</span><span>Reservation = occupied safety envelope</span></div>
<div class="source">Conceptual flow of paper Fig. 4; lane-change controller [20]</div>

<!--
[1:15 | total 5:30]

This is a simplified reading of the timed automaton, not its full guards. The car first announces an intention by claiming an adjacent lane. A potential collision means another reservation or claim overlaps that claimed space.
Click 1: if a conflict appears, withdraw the claim. No manoeuvre has begun.
Click 2: after the claim phase without a conflict, upgrade the claim to a reservation. Complete the lane change and release the old lane. In the abstract controller, spatial guards and timing conditions jointly maintain the invariant that different cars' reservations do not overlap.
Point at the formula to connect claim and reservation to the operators just introduced. This is prior theory on which the tools build, rather than a new controller proof in this paper.
Transition: a city adds intersections and paths through them.
-->

---

# UMLSL extends the view through crossings

<div class="visual-split">
<div><UrbanModel /></div>
<div class="labels"><p><b>Lane segments</b><br>Roads between crossings</p><p><b>Crossing segments</b><br>Paths through intersections</p><p><Tex e="\mathit{cs}" />: this space is in a crossing</p></div>
</div>
<div class="takeaway">A virtual lane follows a path through the road network.</div>
<div class="source">Paper §3.1–3.2; urban model of Schwammberger [32]</div>

<!--
[1:15 | total 6:45]

Schwammberger extends the model and the logic to urban traffic. The result is UMLSL.

The road network has vertical and horizontal roads, their lanes, and intersections. It forms a graph. The nodes are lane segments, the parts of a lane between two intersections, and crossing segments. Directed edges connect segments along the driving direction. Undirected edges connect adjacent lane segments.

Far from an intersection, each virtual lane is one lane segment. Near an intersection, a virtual lane is a sequence of lane and crossing segments. It is one possible path through the crossing. The view of E runs into the crossing.

UMLSL adds the atom cs. It says that the observed space lies on crossing segments.

An example from the paper: "re of E chop cs" does not hold here. Some space separates the reservation of E from the intersection.

The diagram is schematic; follow E’s horizontal path and D’s turn. Transition: the claim protocol now has to protect an entire crossing path.
-->

---

# Reserve enough space to leave the crossing

<div class="visual-split">
<div><UrbanModel /></div>
<div class="labels"><p><b>Before entry</b><br>Claim the intended path.</p><p><b>On commitment</b><br>Reserve the path and room beyond it.</p><p class="safe"><b>Enter only with a reservation.</b></p></div>
</div>
<div class="takeaway">The same claim–check–reserve principle applies to urban manoeuvres.</div>
<div class="source">Paper §3.3; crossing controller [32]</div>

<!--
[1:00 | total 7:45]

Keep the same figure on screen so the audience can focus on D rather than learn another picture. Trace D's reservation down into the crossing, then left into its exit lane. It covers the entire path plus at least the car's own length beyond the intersection. This is why reserving only the crossing itself would be insufficient: the car must be able to leave it.
The controller again claims, checks for potential collision, reserves, then releases what it has left. Reservation exclusivity is the safety invariant; progress through crowded traffic is a separate concern we will return to in the simulator.
We now have the ingredients needed to understand the tools: roads and paths, safety envelopes, local views, spatial formulas, and guarded actions.
Transition: UMLSL-Edit puts these ingredients directly on a canvas.
-->

---
section: UMLSL-Edit
---

# UMLSL-Edit makes the model visible

<div class="visual-split">
<div class="crop-frame editor-focus"><img src="/shots/edit_canvas.png" alt="Editor canvas with five cars, safety envelopes and ego E’s highlighted view"></div>
<div class="labels"><p><b>Direct manipulation</b><br>Roads and cars on a canvas</p><p><b>Automatic geometry</b><br>Crossings, paths, envelopes</p><p><b>Ego perspective</b><br>The selected car’s view</p></div>
</div>
<div class="takeaway">Build a formal traffic snapshot without constructing its graph by hand.</div>
<div class="source">Paper §4.1; real toolkit screenshot, one-crossing sample</div>

<!--
[1:15 | total 9:00]

This is a focused screenshot of the actual editor. Use the large car letters as anchors: E is selected and its visible region is highlighted; A is ahead on the neighboring lane. The faded colored regions are safety envelopes, not vehicle bodies.
Roads and cars can be arranged visually. Intersections and their segments follow from the roads; crossing paths follow from turn intentions; envelopes follow from the vehicle state. Dragging a car changes a formal snapshot rather than merely a drawing.
The infinite canvas and automatic construction reduce the manual effort needed to create examples and corner cases. This is a usability feature, not a measured speedup in authoring time.
Transition: the payoff is that formulas can be evaluated against the scene we can see.
-->

---

# Queries turn the picture into an answer

<div class="query-showcase">
<img class="shot" src="/shots/edit_queries.png" alt="Three evaluated UMLSL queries: safety true, gap true, adjacency to crossing false">
<div class="query-meanings"><p><b class="safe">True</b> · A has no reservation overlap</p><p><b class="safe">True</b> · E has a free gap longer than 2</p><p><b class="unsafe">False</b> · E’s reservation touches a crossing</p></div>
</div>
<div class="takeaway">Readable formulas, explicit ego car, a verdict on the current snapshot.</div>
<div class="source">Paper §4.2; screenshot of the same one-crossing scene</div>

<!--
[1:20 | total 10:20]

Read the screenshot from top to bottom, translating each mathematical statement into the label beside it. The colored letter identifies the ego car for each query; it is not the truth value. The verdict is the border: the bottom query is false.
The gap formula combines a reservation, horizontal chop, a length constraint and free space. Free means no car claims or reserves any positive-length part of that space. The third formula is false because E’s reservation and the crossing are separated by a gap. There is no contradiction: being a safe distance away makes the adjacency formula false.
The editor accepts LaTeX-like input and displays mathematical notation. The result concerns this snapshot and this ego view. It does not assert that every future simulation state will satisfy the query.
Transition: what makes these answers exact when positions are continuous?
-->

---
section: Model checking
clicks: 1
---

# Most checks are finite; one is not obvious

<div class="check-grid">
<div class="box box-grey"><b>Atoms and Boolean operators</b><p>Check the current space.</p></div>
<div class="box box-grey"><b>Quantification</b><p>Range over cars in the view.</p></div>
<div class="box box-grey"><b>Vertical chop</b><p>Try the lane boundaries.</p></div>
<div v-click="1" class="box box-safe"><b>Horizontal chop</b><p>Where should we split a continuous interval?</p></div>
</div>
<div class="takeaway"><Tex e="TS, V(E)\models\varphi" /> — follow the formula on progressively smaller spaces.</div>
<div class="source">Paper §4.2</div>

<!--
[1:15 | total 11:35]

The checker follows the meaning of the formula recursively. For atoms, check containment in reservation, claim, or crossing intervals on a single virtual lane. Boolean operators leave the space unchanged. Quantification ranges over finitely many relevant cars. Vertical chop considers the finite lane sequence, including empty boundary parts as allowed by the semantics.
Only chop changes the observed space. Click to expose the difficulty: a horizontal split r could be any real point from b to e. We cannot enumerate an uncountable interval.
This is the theoretical contribution that makes the graphical checker possible: reduce the continuous choice to a finite set while preserving the answer. No parser or software architecture detail is needed to understand the problem.
Transition: why not just use the pixels of the editor?
-->

---

# A fixed grid can miss the witness

<div class="wide-diagram" style="width:850px">
<svg viewBox="0 0 850 220" role="img" aria-label="A narrow witness interval lies between sampling grid points">
<line x1="50" x2="800" y1="110" y2="110" stroke="#002d4c" stroke-width="3" />
<path v-for="i in 16" :d="`M${50+(i-1)*50},98v24`" stroke="#a8b9c4" stroke-width="3" />
<rect x="418" y="80" width="16" height="60" fill="#002d4c" />
<text x="426" y="55" text-anchor="middle" fill="#002d4c" style="font-size:22px">valid splits</text>
<text x="50" y="153" style="font-size:22px">b</text><text x="790" y="153" style="font-size:22px">e</text>
<text x="425" y="192" text-anchor="middle" fill="#445e6f" style="font-size:20px">Every grid point misses this interval.</text>
</svg>
</div>
<div class="takeaway">Choose candidates from the scene and the formula, rather than a fixed resolution.</div>
<div class="source">Paper §4.2; schematic illustration, not benchmark data</div>

<!--
[0:50 | total 12:25]

The gray ticks are candidate splits on a fixed grid. The dark interval is a set of witnesses between two ticks. Even a narrow valid space matters to exact semantics. A failed search on a grid therefore cannot establish that the formula is false.
The paper instead uses critical points tied to the boundaries of the scene and the constants in the formula. It remains a finite search, but one designed around where truth can change.
Pause and point at the dark interval before advancing. Transition: construct those candidates on the gap example.
-->

---
clicks: 3
---

# Critical points capture the relevant splits

<p class="formula-lead"><Tex e="\varphi=\mathit{re}(E)\frown(\ell>2\land\mathit{free})" /> <span class="muted">· one lane, chop depth 1</span></p>
<div class="wide-diagram" style="width:700px"><CriticalPoints :step="$clicks + 1" /></div>
<div class="cp-legend"><span>● boundaries</span><span v-click="1">□ length offsets</span><span v-click="2">▲ gap representatives</span><span v-click="3"><b>│ witness</b></span></div>
<div class="source">Paper §4.2 and App. A, Def. A.1; illustrative coordinates</div>

<!--
[2:15 | total 14:40]

Here is the construction on a small example. One lane, an interval from b to e. Car E reserves the start of the interval. A crossing segment lies further ahead. The formula is "re of E chop, length greater than 2 and free". It has one constant, 2, and one horizontal chop. So d is 1.

Initially: first, the base points. These are b, e, and every endpoint of a reservation, a claim, or a segment inside the interval. We take them over all lanes in the space and all cars in the view. An atom can change its truth value only at these points.

Click 1. Second, the offsets. K of phi is the set of constants k in length comparisons in phi. d is the nesting depth of horizontal chops. We add b plus or minus s and e plus or minus s, where s is a sum of at most d constants, with repetition. Here we get b plus 2 and e minus 2. The other two points fall outside the interval.

Click 2. Third, the midpoints. Between each pair of adjacent points so far, we add one representative. We take the midpoint.

The union of the three sets is CP of V and phi.

Click 3. The checker tries the elements of CP as chopping points. It succeeds as soon as one point splits the space so that both operands hold. Here r at the end of the reservation of E works. To the left, E reserves the space. To the right, the space is free and longer than 2.

Spend time tracing the candidate construction; this is the centerpiece of the checker explanation. The example is an observed single-lane subspace, not a claim that the entire ego view has one lane.
-->

---

# Why a finite search can be exact

<div class="theorem"><b>Theorem 4.1</b> · checker returns true <Tex e="\Longleftrightarrow TS,V(E)\models\varphi" /></div>
<div class="wide-diagram" style="width:700px"><CellsDiagram /></div>
<div class="definition-strip"><span><b>Sound:</b> every successful split is a witness.</span><span><b>Complete:</b> every witness has a representative.</span></div>
<div class="source">Paper §4.2 and App. A; cell argument shown here for the length-free case</div>

<!--
[1:25 | total 16:05]

Theorem 4.1 says that the checker returns true if and only if the formula holds. Here is the intuition. The full proof is in the appendix of the paper.

Soundness is simple. Every chopping candidate lies in the interval from b to e. So a positive answer always shows a real witness. This holds for every formula.

For completeness, first take formulas without length comparisons. The intervals of crossing segments, reservations and claims change their membership only at base points. So each of them is constant on each cell. A cell is either one base point or one open interval between two adjacent base points.

So whether a formula holds depends on b and e only through the cells that they lie in. A witness s of a chop can move to the representative of its cell. The midpoint m is in the same cell, so m is a witness too. And the base points plus the midpoints contain one representative for each cell.

Point at s and m and allow a pause: exactness comes from equivalent cells, not from making a grid finer. Transition: length tests add extra boundaries.
-->

---

# Length tests refine the candidate set

<div class="wide-diagram" style="width:780px"><OffsetsDiagram /></div>
<div class="definition-strip"><span><Tex e="\ell\sim k" /> adds distance <Tex e="k" /></span><span>Depth <Tex e="d" /> accumulates up to <Tex e="d" /> constants</span></div>
<div class="takeaway">A chosen split becomes a new anchor in the smaller space.</div>
<div class="source">Paper §4.2 and App. A</div>

<!--
[1:00 | total 17:05]

Now add length comparisons. A comparison l similar to k depends only on the length of the space. So it refines the cells by the constant k.

A chain of d nested chops adds up at most d of these constants. The offsets supply exactly these points.

Why only offsets from b and e? A chop that splits at an interior point s recurses on spaces that s bounds. At that level, the checker computes the offsets again, with s as an anchor. So the required point is always a candidate.

Together, these two arguments give Theorem 4.1.

Keep the proof at the level of this picture; the appendix contains the full argument.
-->

---

# Exact checking has a measurable cost

<div class="chart-split"><div><TimesChart /></div><div class="labels">
<p><b>Locality helps</b><br>F1–F4 vary by ≤2% when total traffic grows from 10 to 80 cars, with 10 in view.</p>
<p><b>Chop depth costs</b><br>F6 has no witness:<br><b>18.2 s → 250.3 s</b></p>
<p>Common queries: milliseconds to about 1.5 s in this experiment.</p>
</div></div>
<div class="source">Paper §6.1, Tables 1–2 · 40 cars, 8 roads · medians · M1 Max, Python 3.14, one thread</div>

<!--
[1:50 | total 18:55]

Use the log axis carefully: each major step is ten times longer. These are the paper's Table 1 values: medians of fifteen samples for F1–F4, and at least three for the slower formulas. F1 asks whether E reserves somewhere; F2 is safety; F3 asks for a gap; F4 excludes the crossing from the gap and is nearly the same as F3 here.
With two to ten cars in view, F1 takes 9 to 66 milliseconds. Safety rises from 34 milliseconds to 1.49 seconds; the gap query from 74 milliseconds to 1.04 seconds. The deep no-witness example F6 rises from 18.2 seconds to 250.3 seconds. Do not call all queries interactive.
The critical-point search grows exponentially with horizontal chop depth; the paper bounds explored spaces by O(|CP|^d). Locality helps: adding cars outside the fixed view changes F1–F4 by at most 2 percent in the reported comparison.
Verdict and placement matter too: false gap queries took 7–12 times longer than true ones, up to 5.8 seconds in Table 2. The editor remains responsive during checks. Transition: the next question is what happens when the cars start moving.
-->

---
section: UMLSL-Sim
---

# A checked snapshot becomes a scenario

<div class="handoff-pair">
<div><div class="crop-frame handoff-editor"><img src="/shots/edit_canvas.png" alt="One-crossing scenario in UMLSL-Edit"></div><b>UMLSL-Edit · spatial properties</b></div>
<div class="large-arrow">→</div>
<div><img class="shot" src="/shots/sim_one_scene.png" alt="The same five-car scenario running in UMLSL-Sim"><b>UMLSL-Sim · evolving traffic</b></div>
</div>
<div class="takeaway">Reuse roads, cars and initial intentions across the two tools.</div>
<div class="source">Paper Fig. 1; repository README, “Exchanging scenarios” · screenshots at different times</div>

<!--
[0:55 | total 19:50]

The five-car example becomes a simulation scenario without reconstructing the road network. The pictures show the editor and a later state of its simulation, so positions have changed. The handoff supports moving between analysis and experiments with little manual setup.
A checked starting condition does not certify the future behavior of a learned policy. The simulator's action constraints are a separate part of the safety story.
The README also explains the limits: only supported scenarios can be exported; representation adjustments are reported. Queries are kept in the editor's native scene and do not travel with the scenario. This is why we describe reuse of scenarios rather than an unconditional lossless transfer of every item.
Transition: how are the formal controller ideas used as traffic evolves?
-->

---

# UMLSL-Sim turns safe choices into traffic

<div class="visual-split">
<img class="shot" src="/shots/sim_two_scene.png" alt="UMLSL-Sim traffic with reservations and goal markers">
<div class="labels"><p><b>Safe controller</b><br>Which actions are allowed?</p><p><b>Optimal controller</b><br>Choose the highest safe acceleration.</p><p><b>Crossing claims expire</b><br>Stalled claims release the way.</p></div>
</div>
<div class="takeaway">Every car acts; then the simulation advances one time step.</div>
<div class="source">Paper §5.1–5.2 · rectangles: cars; lines: safety envelopes; rings: goals</div>

<!--
[1:15 | total 21:05]

The screenshot shows eight roads with sixteen intersections. Colored rectangles are vehicles, lines show envelopes, and matching rings mark goals. Within each frame every car chooses controller actions, then time advances.
Distinguish the safe controller, which computes admissible acceleration and lane-change choices, from the optimal controller, which chooses the largest safe acceleration and a lane that permits a higher one. Optimal here means this local driving objective, not a globally optimal traffic schedule.
The traffic controllers draw on the lane-change controller of Hilscher, the crossing controller of Schwammberger and the cruise controller of Larsen. The safety results in prior work concern the abstract model; measured outcomes provide evidence about these executions.
Crossing claims are leases. A car that makes no progress cannot retain a claim forever. This bounds waiting caused by a stalled claim, but does not guarantee that the entire traffic network stays free of gridlock.
Transition: how fast does this run, and where does it stop?
-->

---

# Measured speed and remaining gridlocks

<div class="chart-split"><div><SimThroughput /></div><div class="metric-column">
<div><b class="metric safe">0 / 150</b><span>episodes with a collision</span></div>
<div><b class="metric">4 / 150</b><span>episodes ending in gridlock</span></div>
<p>16–48 cars · 30 episodes each<br>Up to 1,500 frames per episode</p>
</div></div>
<div class="takeaway">Useful for repeated experiments; dense traffic still costs more.</div>
<div class="source">Paper §6.2, Table 3 · NPCs only, headless · M1 Max, Python 3.14, one thread</div>

<!--
[1:05 | total 22:10]

This is simulation throughput, not the screen refresh rate and not an RL training speed benchmark. At sixteen cars the reported rate is 257 frames per second; at forty-eight it is 28.5. Tripling the traffic raises time per frame roughly ninefold. This is consistent with pairwise checks becoming expensive.
The repository measures throughput separately from episode outcomes: three placements, five repeats, fastest repeat for each placement, then average frame time. It is a controlled timing estimate, not guaranteed performance on every machine.
For outcomes, thirty episodes at each of five densities give 150 total. None collided; four ended in gridlock, all at 32 or more cars. These are observations on the tested scenario, not a universal liveness proof. A finite window of stopped traffic indicates gridlock but does not prove a state is permanently deadlocked.
Transition: the same environment can also ask how a learning agent behaves among these cars.
-->

---

# One learning agent among controlled traffic

<div class="visual-split"><img class="shot" src="/shots/sim_agent.png" alt="A trained agent and NPC traffic in UMLSL-Sim"><div class="labels">
<p><b>Agent car</b><br>Acceleration + lane choice</p><p><b>Surrounding traffic</b><br>NPCs use the optimal controller</p><p><b>Compare experiments</b><br>Train, evaluate, replay</p></div></div>
<div class="takeaway">Change the objective and observation; keep the traffic model fixed.</div>
<div class="source">Paper §5.3 · Gymnasium environment · screenshot: trained agent replay</div>

<!--
[1:05 | total 23:15]

The simulator supports training, evaluation and replay through one environment. The agent controls one designated car; the remaining cars follow the controller. Its action has the same structure as the controller's: acceleration and lane-change direction. The observation describes surrounding traffic and the reward expresses an objective.
Configurable rewards and observations let researchers compare choices without rebuilding the scenario. The control interface exposes these experiment options; we do not need a menu tour to appreciate the capability.
The screenshot is a replay illustration, not the one-crossing benchmark shown later. Episodes end on collision, detected gridlock or a step limit. A useful question is whether the safe controller should influence learning as a penalty or as a restriction.
Transition: these are different uses of the same safety verdict.
-->

---
clicks: 1
---

# Penalise an unsafe action—or exclude it

<div class="wide-diagram" style="width:860px"><SafetyMechanisms :step="$clicks" /></div>
<div class="question-pair"><div><b>Reward shaping</b><span>Safety competes with the objective.</span></div><div v-click="1"><b>Action shielding</b><span>The reward can focus on progress.</span></div></div>
<div class="source">Paper §5.3 · permitted actions are those accepted by the safe controller</div>

<!--
[1:25 | total 24:40]

Explain the left row first: all choices remain available. Red squares are choices the controller rejects, and a safety-aware reward penalises them after the step. PPO must learn to trade that penalty against other reward terms. There is no guarantee that it will avoid such a choice.
Click once: the right row removes those same choices before action selection. MaskablePPO uses the safe controller as an action mask. Each permitted choice is accepted by the controller at every stage of training. Safety here is relative to the model and controller assumptions, not a claim about deployment on real roads.
The mask remains nonempty: maximum braking with no lane change is available. There is still a choice among safe actions; the paper reports around seventeen of sixty-three pairs allowed on average.
The visual timing is the point: penalty after acting versus exclusion before acting. Transition: does that difference show up in the experiment?
-->

---

# Shielding preserves room for progress

<PolicyResults />
<div class="takeaway">In this experiment, a safety penalty suppressed progress; the shield did not.</div>
<div class="source">Paper §6.3, Table 4 · 15 NPCs + 1 agent · 100k training steps, 3 seeds · 30 evaluation episodes / seed</div>

<!--
[1:30 | total 26:10]

First identify the columns: crash rate is the fraction of evaluation episodes with a crash; goals is the mean total over thirty episodes per seed, not goals per episode. The three trained policies use one hundred thousand training steps with default hyperparameters and three seeds. Training took about four minutes per run on the reported laptop.
Random policy: shielding reduces its crash rate from 74 percent to zero even though it learns nothing. PPO with the initial reward crashes in 43 percent of episodes and reaches 20.3 goals. The safety-aware reward avoids crashes in this sample but reaches zero goals to the displayed precision: it learned to move very cautiously. Shielded MaskablePPO reaches 41 goals with no observed crash.
This is one scenario and training budget, not a general ranking of learning algorithms. Reward shaping can behave differently with other tuning. The lesson supported here is that keeping unsafe actions outside the available choices lets the reward focus on progress.
Source detail: the paper's 88,280 shielded steps pools random-shielded and learned-shielded evaluation; do not attribute that total only to the learned agent. Transition: a run can also generate new states for formal inspection.
-->

---

# Return an observed state to formal analysis

<div class="handoff-pair">
<div><img class="shot" src="/shots/sim_handoff.png" alt="Paused simulator state"><b>Observe a run</b></div>
<div class="large-arrow">→</div>
<div><img class="shot" src="/shots/edit_handoff.png" alt="Simulation state opened for queries in UMLSL-Edit"><b>Apricot: safe ✓ · gap &gt; 2 ✕</b></div>
</div>
<div class="takeaway">Simulation produces new questions; UMLSL-Edit checks them spatially.</div>
<div class="source">Paper Fig. 1; repository README, “UMLSL-Sim ➜ UMLSL-Edit”</div>

<!--
[1:00 | total 27:10]

The loop closes here. A running or paused simulation can hand a state back to the editor. This supports investigation of a learned agent's behavior or a congested arrangement: take the state, choose an ego car, and pose a spatial question.
In this captured example, the safety query for Apricot holds while the gap query does not. These are different statements: lack of a gap does not by itself mean a collision. The full windows establish the handoff; do not ask the audience to read their tiny UI text.
Imported snapshots may need representation adjustments, which the tools report; formulas must be added or kept separately because queries are not transferred. Interpret the formal answer on the imported snapshot. It is a diagnostic loop, not a temporal proof over the entire run.
Transition: return to the two motivating questions and summarize what the paper contributes.
-->

---
section: Conclusion
---

# Conclusion: UMLSL becomes executable

<div class="conclusion-grid"><div>
<div class="contribution"><b>UMLSL-Edit</b><span>Visual scenarios + sound, complete formula checking</span></div>
<div class="contribution"><b>UMLSL-Sim</b><span>Controller-based traffic + safety-guided learning</span></div>
<div class="contribution"><b>Connected workflow</b><span>Specify → simulate → re-analyse</span></div>
<div class="future"><b>Future work</b><p>Faster checking · fewer gridlocks<br>Roundabouts, pedestrians, signals · timed properties</p></div>
</div><div class="qr-block">
<a href="https://github.com/MASE-Group/umlsl-tk"><img src="/qr-umlsl-tk.png" alt="Scan for the UMLSL-TK GitHub repository"></a>
<b>Code, examples & benchmarks</b><span>github.com/MASE-Group/umlsl-tk</span>
</div></div>
<div class="source">Paper §7 · Questions welcome</div>

<!--
[1:15 | total 28:25]

The contribution is a practical connection between a spatial logic and executable traffic. UMLSL-Edit makes snapshots visible and decides formulas using the critical-point procedure proved sound and complete. UMLSL-Sim makes controller behavior and learning experiments observable, including two ways to use the safe controller. The bidirectional workflow connects the two.
The evidence also tells us what to improve: deeply nested checks can be expensive, and dense traffic can still gridlock. Immediate work targets checker efficiency and the crossing claim protocol. Longer-term work includes merging and splitting lanes, roundabouts, pedestrians and signals, with matching logic extensions; timed properties, real-time simulation and continuous actions are also planned.
The QR code links to the repository containing the tools, documentation, examples and reproducible benchmark records. Leave this slide visible during questions. Thank the audience.
-->
