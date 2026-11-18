---
title: "Edit, Check, Simulate and Train: A Toolkit for UMLSL"
info: |
  SBMF 2026, Rio de Janeiro, Brazil, 02.12.2026.
  Talk on UMLSL-TK: UMLSL-Edit and UMLSL-Sim.
canvasWidth: 960
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
exportFilename: umlsl-tk-sbmf2026
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
[0:20 | total 0:20]

Welcome. This talk presents UMLSL-TK, a toolkit for Urban Multi-Lane Spatial Logic.

The toolkit has two tools. UMLSL-Edit builds traffic scenarios and checks UMLSL formulas on them. UMLSL-Sim simulates these scenarios and trains reinforcement learning agents on them.

The picture shows UMLSL-Sim on the two-crossings scenario.
-->

---
section: Motivation
---

# Why formal traffic analysis?

<div class="grid grid-cols-2 gap-6 mt-2">
  <div class="box box-grey">
    <div class="box-title">Test drives</div>
    Alone, they are not sufficient to prove safety.
  </div>
  <div class="box box-safe">
    <div class="box-title">Formal specification and verification</div>
    They need tool support.
  </div>
</div>

<div class="gap-row">
  <div class="gap-end">Abstract spatial logic</div>
  <div class="gap-mid"><span>gap</span></div>
  <div class="gap-end">Executable, trainable environments</div>
</div>
<div class="bridge">UMLSL-TK bridges this gap for UMLSL</div>

<style>
.gap-row { display: flex; align-items: center; margin-top: 44px; }
.gap-end { flex: none; width: 250px; padding: 14px 10px; text-align: center; background: var(--kit-iceblue-15); border: 1.5px solid var(--kit-iceblue-50); font-weight: 700; }
.gap-mid { flex: 1; text-align: center; border-top: 2px dashed var(--kit-iceblue-50); position: relative; }
.gap-mid span { position: relative; top: -12px; background: #fff; padding: 0 8px; color: var(--kit-iceblue-70); font-size: 14px; }
.bridge { margin-top: 16px; text-align: center; color: var(--kit-green); font-weight: 700; border-top: 3px solid var(--kit-green); padding-top: 8px; }
</style>

<!--
[0:50 | total 1:10]

Autonomous and semi-automated driving functions promise safer and more comfortable mobility.

Research shows that test drives alone are not sufficient to prove safety. So we also need other means, such as formal specification and verification. Formal methods need tool support to check system properties in a systematic way.

A gap remains between abstract spatial logics and environments that we can execute and train in. To bridge it is not trivial. Tools must handle run-time situations and corner cases. They must also work with modern machine learning frameworks.

UMLSL-TK bridges this gap for UMLSL.
-->

---
section: Background
---

# MLSL: the highway model

<div class="mx-auto" style="width: 640px">
  <MlslView />
</div>

<ul class="mt-1">
  <li>Lanes are discrete. Positions along the lanes are continuous.</li>
  <li>A claim announces a lane change, like a turn signal.</li>
</ul>

<!--
[1:15 | total 2:25]

UMLSL extends the highway traffic model and the Multi-Lane Spatial Logic, MLSL, of Hilscher et al. So we start on the highway.

Each car reserves the space of its safety envelope. The envelope covers the size of the car, its stopping distance, and a buffer. With it, a car can always stop without hitting the car in front.

Before a lane change, a car first claims space on the adjacent lane. Here, C claims space on lane 1. The claim tells the other cars what C wants to do, like a turn signal.

Formulas are evaluated from the view of one car, the ego car E. The virtual view reaches a fixed horizon h backwards and forwards from E. The set of lanes in the view is discrete. The interval along the lanes is continuous. Car A is outside the view, so formulas for E do not see it.
-->

---

# Formulas chop the view

<div class="grid gap-6" style="grid-template-columns: 1.15fr 1fr">
<div>
  <ChopDiagram />
</div>
<div class="formulas">

Atoms: $\mathit{re}(C)$, $\mathit{cl}(C)$, $\ell \sim k$

Somewhere: $\langle\varphi\rangle \equiv \begin{array}{c}\mathit{true}\\\hline \mathit{true}\frown\varphi\frown\mathit{true}\\\hline \mathit{true}\end{array}$

$\mathit{free} \equiv \neg\exists c\colon \langle \mathit{re}(c) \lor \mathit{cl}(c)\rangle$

<span class="safe"><Tex e="\mathit{safe} \equiv \neg\exists c\colon c \neq E \land \langle \mathit{re}(c) \land \mathit{re}(E)\rangle" /></span>

</div>
</div>

<style>
.formulas p { margin: 0 0 12px 0; }
</style>

<!--
[1:15 | total 3:40]

A formula is evaluated over an observed space. That is a set of lanes and an interval along them. Evaluation starts with the whole virtual view.

The horizontal chop splits the space at a point r along the lanes. phi 1 must hold before r, and phi 2 after r. The vertical chop splits the space at a lane border. phi 1 holds below, and phi 2 holds above.

The atoms re of C and cl of C need exactly one lane. They say that car C reserves, or claims, all of that space. The symbol l is the length of the space, and we compare it with constants.

From these parts we get "somewhere", "free", and the safety property. "safe" says that no other car reserves space that E also reserves.

We use the syntax that the paper gives for UMLSL. We leave out only the crossing atom cs. It comes with the urban model in two slides.
-->

---

# Lane-change controller

<div class="grid gap-6 items-center" style="grid-template-columns: 1.25fr 1fr">
<div>
  <ControllerTA variant="lane" />
</div>
<div>

<p class="unsafe small"><b>Potential collision</b></p>

$\mathit{pc}(\mathit{ego}) \equiv \exists c\colon c \neq \mathit{ego} \land \langle \mathit{cl}(\mathit{ego}) \land (\mathit{re}(c) \lor \mathit{cl}(c))\rangle$

<ul class="mt-4">
  <li>A car reserves only claimed space with no potential collision.</li>
  <li class="safe"><b>So reservations of different cars never overlap.</b></li>
</ul>

</div>
</div>

<!--
[1:15 | total 4:55]

Hilscher et al. define a lane-change controller as a timed automaton. MLSL formulas are part of its guards and invariants. So the automaton can reason about space and time together.

From idle, the ego car claims the adjacent lane segment. It resets the clock x.

While ego holds the claim, the controller checks for a potential collision. A potential collision means that another car claims or reserves the space that ego claims. That is the formula pc of ego.

If pc becomes true, ego withdraws the claim and goes back to idle. If pc stays false for the claim time, ego turns the claim into a reservation and starts the manoeuvre. After the manoeuvre time, ego releases the space that it left. It keeps only the new lane segment n.

The safety proof rests on this flow. A car reserves only space that it first claimed without a potential collision. So the reservations of different cars never overlap.
-->

---

# UMLSL: the urban model

<div class="grid gap-5 items-center" style="grid-template-columns: 1.3fr 1fr">
<div>
  <UrbanModel />
</div>
<div>
<ul>
  <li>Road network: a graph of lane segments and crossing segments.</li>
  <li>Virtual lane: one path through the crossing.</li>
  <li>New atom <Tex e="\mathit{cs}" />: the space lies in an intersection.</li>
  <li>Here <Tex e="\langle \mathit{re}(E) \frown \mathit{cs}\rangle" /> is false. A gap separates the two.</li>
</ul>
</div>
</div>

<!--
[1:15 | total 6:10]

Schwammberger extends the model and the logic to urban traffic. The result is UMLSL.

The road network has vertical and horizontal roads, their lanes, and intersections. It forms a graph. The nodes are lane segments, the parts of a lane between two intersections, and crossing segments. Directed edges connect segments along the driving direction. Undirected edges connect adjacent lane segments.

Far from an intersection, each virtual lane is one lane segment. Near an intersection, a virtual lane is a sequence of lane and crossing segments. It is one possible path through the crossing. The view of E runs into the crossing.

UMLSL adds the atom cs. It says that the observed space lies on crossing segments.

An example from the paper: "re of E chop cs" does not hold here. Some space separates the reservation of E from the intersection.
-->

---

# Crossing controller

<div class="grid gap-6 items-center" style="grid-template-columns: 1.25fr 1fr">
<div>
  <ControllerTA variant="crossing" />
</div>
<div>
<ul>
  <li>Same flow: claim, check, reserve, withdraw.</li>
  <li>Claim: the path through the next crossing.</li>
  <li>Reserve: that path plus at least the car's own length beyond it.</li>
  <li class="safe"><b>Enter only with a reservation.</b></li>
</ul>
</div>
</div>

<!--
[1:15 | total 7:25]

Schwammberger defines the crossing controller with the same claim, check, reserve and withdraw flow. Here UMLSL formulas are part of the guards and invariants.

The car claims its path through the next crossing. Again it checks for a potential collision. If none occurs, it turns the claim into a reservation.

When a car is in or near a crossing, it reserves its whole path through the intersection. It also reserves at least its own length beyond the intersection. So the car can always clear an intersection that it enters.

After the crossing, the car releases the crossing segments.

The same argument as before gives safety. A car enters a crossing segment only with a reservation of it.
-->

---
section: UMLSL-Edit
---

# UMLSL-Edit: build a scenario

<div class="grid gap-5" style="grid-template-columns: 540px 1fr">
<div>
  <img class="shot" src="/shots/edit_main.png" style="width: 540px">
</div>
<div>
  <img class="shot" src="/shots/edit_car.png" style="width: 128px">
  <div class="shot-cap">Car dialog</div>
  <ul class="mt-3 small">
    <li>Add roads. The tool creates the crossings.</li>
    <li>Place cars: lane, position, speed, acceleration, next turn.</li>
    <li>Move cars by drag and drop.</li>
  </ul>
</div>
</div>

<!--
[1:30 | total 8:55]

UMLSL-Edit is the first tool. It is a visual editor and model checker for UMLSL. The user builds a scenario on an infinite canvas.

This is a sample scene with one crossing and five cars. We simulate the same scene later.

The user adds vertical or horizontal roads. Each road can have any number of lanes in both directions, in right-hand traffic. Where two roads intersect, the tool creates the lane segments and crossing segments.

Then the user places cars. Each car has a lane, a position, a speed, and an acceleration. A car can also claim or reserve an adjacent lane. The user gives the next turn of the car. From it, the tool computes the path through the crossing segments. The tool reserves space from the size and the safety envelope of the car.

Cars move by drag and drop.
-->

---

# UMLSL-Edit: write and check queries

<div class="grid gap-5 items-start" style="grid-template-columns: 250px 340px 1fr">
<div>
  <img class="shot" src="/shots/edit_query.png" style="width: 250px">
  <div class="shot-cap">Query dialog</div>
</div>
<div>
  <img class="shot" src="/shots/edit_queries.png" style="width: 340px">
  <div class="shot-cap">Queries of the scene, checked in the view of their car</div>
</div>
<div>
<ul class="small">
  <li>Select a car. Its virtual view appears.</li>
  <li>Type the query in a LaTeX-like syntax. The tool shows it in mathematical notation.</li>
  <li>The checker decides each query in the view of its car.</li>
</ul>
</div>
</div>

<!--
[1:30 | total 10:25]

When the user selects a car, the tool shows its virtual view. Each query belongs to one ego car. The checker evaluates it in the view of that car.

Queries use a LaTeX-like syntax. The tool documents the syntax in a help dialog. It parses each query and shows it in mathematical notation.

Here are three queries. The first one is the safety property for car A. It holds. The second one asks for a gap of more than 2 units ahead of the reservation of E. It holds too. The third one is the example from before: re of E chop cs. It does not hold, because space separates E from the crossing. The tool marks a false query in red.

UMLSL-Edit decides formulas in a separate process. So the editor stays responsive while the checker works.
-->

---
section: Model checking
clicks: 5
---

# Model checking: a recursive descent

<p class="muted small" style="margin-top:-6px">Decide <Tex e="TS, V(E) \models \varphi" />. Start with the observed space <Tex e="V(E)" />.</p>

<div class="rules">
  <div v-click="1" class="rule"><SpaceGlyph kind="atom" /><span><b>Atom:</b> test <Tex e="[b,e] \subseteq \mathit{CS}_l, \mathit{RE}_l(C), \mathit{CL}_l(C)" />. False if <Tex e="|L| \neq 1" />.</span></div>
  <div v-click="2" class="rule"><SpaceGlyph kind="same" /><span><b><Tex e="\neg, \land, \lor" />:</b> recurse on the same space.</span></div>
  <div v-click="3" class="rule"><SpaceGlyph kind="cars" /><span><b><Tex e="\exists c" />:</b> one call for each car in the view. The set is finite.</span></div>
  <div v-click="4" class="rule"><SpaceGlyph kind="vchop" /><span><b>Vertical chop:</b> try each lane border. There are finitely many.</span></div>
  <div v-click="5" class="rule"><SpaceGlyph kind="hchop" /><span><b>Horizontal chop:</b> try chopping points <Tex e="r \in [b, e]" />. Which ones?</span></div>
</div>

<style>
.rules { display: flex; flex-direction: column; gap: 12px; margin-top: 10px; }
.rule { display: flex; align-items: center; gap: 14px; }
</style>

<!--
[1:30 | total 11:55]

Now the main part: the model checker.

Input: a traffic snapshot TS, an ego car E, and a query phi. The checker decides whether phi holds over the virtual view of E. It follows the semantics of UMLSL.

The check is a recursive descent over the structure of phi. It carries the current observed space. The first call gets the whole virtual view.

Click. An atom is decided directly. The checker tests whether the interval is inside a crossing segment, a reservation, or a claim on the one lane. If the space has more than one lane, the atom fails at once.

Click. Boolean connectives recurse on the same space.

Click. The quantifier ranges over the cars in the view. That set is finite, so there is one recursive call for each car.

Click. The vertical chop tries each lane border. There are finitely many.

Click. Only the chop operators make the space smaller. And the horizontal chop has a problem. Its chopping point r can be any point in the interval.
-->

---

# The problem: a continuous chopping point

<div class="mx-auto" style="width: 660px">
<svg viewBox="0 0 660 120" style="width:100%; font-family: var(--kit-font-body)">
  <line x1="40" x2="620" y1="50" y2="50" stroke="#002d4c" stroke-width="1.5" />
  <g stroke="#a8b9c4" stroke-width="1.5">
    <line v-for="i in 30" :key="i" :x1="40 + (i - 1) * 20" :x2="40 + (i - 1) * 20" y1="42" y2="58" />
  </g>
  <rect x="345" y="30" width="12" height="40" fill="#002d4c" opacity="0.85" />
  <text x="351" y="22" style="font-size:12px; text-anchor:middle; fill:#002d4c">witnesses</text>
  <text x="40" y="82" style="font-size:14px; text-anchor:middle; font-style:italic; fill:#445e6f">b</text>
  <text x="620" y="82" style="font-size:14px; text-anchor:middle; font-style:italic; fill:#445e6f">e</text>
  <text x="330" y="108" style="font-size:12px; text-anchor:middle; fill:#445e6f">grid points (grey ticks) can miss every witness</text>
</svg>
</div>

<ul class="mt-4">
  <li><Tex e="r" /> ranges over the continuous interval <Tex e="[b, e]" />.</li>
  <li>A pixel grid gives a sound procedure. It is incomplete and highly inefficient.</li>
  <li>Our approach: a finite set of critical points, with no discretisation. It is sound and complete.</li>
</ul>

<!--
[0:50 | total 12:45]

All UMLSL operators range over finite sets, with one exception. The chopping point r of the horizontal chop ranges over the continuous interval from b to e.

One idea is to discretise this interval, for example along the pixel grid of the visual editor. The result is sound but incomplete. It is also highly inefficient. In the picture, all witnesses lie between two grid points, so the grid finds none.

We use a critical-point construction instead. The set of candidates is finite without any discretisation. We prove that the procedure is sound and complete.
-->

---
clicks: 4
---

# Critical points $CP(V, \varphi)$

<p class="muted small" style="margin-top:-6px">Example on one lane: <Tex e="\varphi = \mathit{re}(E) \frown (\ell > 2 \land \mathit{free})" />, so <Tex e="K(\varphi) = \{2\}" /> and <Tex e="d = 1" />.</p>

<div class="grid gap-5 items-center" style="grid-template-columns: 540px 1fr">
<div>
  <CriticalPoints :step="$clicks" />
</div>
<div class="small legend">
  <p v-click="1"><b>● Base:</b> <Tex e="b" />, <Tex e="e" />, and each endpoint of a reservation, claim or segment</p>
  <p v-click="2"><b>□ Off:</b> <Tex e="b \pm s" />, <Tex e="e \pm s" />, where <Tex e="s" /> sums at most <Tex e="d" /> constants of <Tex e="K(\varphi)" /></p>
  <p v-click="3"><b>▲ Mid:</b> one midpoint in each open gap</p>
  <p v-click="4"><b>Try each point as <Tex e="r" />.</b> Stop when both sides hold.</p>
</div>
</div>

<style>
.legend p { margin: 0 0 12px 0; }
</style>

<!--
[2:15 | total 15:00]

Here is the construction on a small example. One lane, an interval from b to e. Car E reserves the start of the interval. A crossing segment lies further ahead. The formula is "re of E chop, length greater than 2 and free". It has one constant, 2, and one horizontal chop. So d is 1.

Click. First, the base points. These are b, e, and every endpoint of a reservation, a claim, or a segment inside the interval. We take them over all lanes in the space and all cars in the view. An atom can change its truth value only at these points.

Click. Second, the offsets. K of phi is the set of constants k in length comparisons in phi. d is the nesting depth of horizontal chops. We add b plus or minus s and e plus or minus s, where s is a sum of at most d constants, with repetition. Here we get b plus 2 and e minus 2. The other two points fall outside the interval.

Click. Third, the midpoints. Between each pair of adjacent points so far, we add one representative. We take the midpoint.

The union of the three sets is CP of V and phi.

Click. The checker tries the elements of CP as chopping points. It succeeds as soon as one point splits the space so that both operands hold. Here r at the end of the reservation of E works. To the left, E reserves the space. To the right, the space is free and longer than 2.
-->

---

# Why the procedure is sound and complete

<div class="box box-grey mb-4">
  <b>Theorem 4.1.</b> The model checker returns true if and only if <Tex e="TS, V(E) \models \varphi" />.
</div>

<div class="grid gap-6" style="grid-template-columns: 1fr 1.5fr">
<div>
  <div class="box-title">Sound</div>
  <p class="small">Each candidate lies in <Tex e="[b, e]" />. So a positive answer always comes with a witness.</p>
</div>
<div>
  <div class="box-title">Complete</div>
  <CellsDiagram />
</div>
</div>

<!--
[1:30 | total 16:30]

Theorem 4.1 says that the checker returns true if and only if the formula holds. Here is the intuition. The full proof is in the appendix of the paper.

Soundness is simple. Every chopping candidate lies in the interval from b to e. So a positive answer always shows a real witness. This holds for every formula.

For completeness, first take formulas without length comparisons. The intervals of crossing segments, reservations and claims change their membership only at base points. So each of them is constant on each cell. A cell is either one base point or one open interval between two adjacent base points.

So whether a formula holds depends on b and e only through the cells that they lie in. A witness s of a chop can move to the representative of its cell. The midpoint m is in the same cell, so m is a witness too. And the base points plus the midpoints contain one representative for each cell.
-->

---

# Length comparisons need the offsets

<div class="mx-auto" style="width: 600px">
  <OffsetsDiagram />
</div>

<ul class="mt-2">
  <li>A comparison <Tex e="\ell \sim k" /> cuts the cells again, at distance <Tex e="k" /> from an anchor.</li>
  <li>A chain of <Tex e="d" /> nested chops adds up at most <Tex e="d" /> constants. That is <Tex e="\mathit{Off}(V, \varphi)" />.</li>
  <li>Offsets start from <Tex e="b" /> and <Tex e="e" /> only. A split point <Tex e="s" /> is an anchor one level down.</li>
</ul>

<!--
[1:00 | total 17:30]

Now add length comparisons. A comparison l similar to k depends only on the length of the space. So it refines the cells by the constant k.

A chain of d nested chops adds up at most d of these constants. The offsets supply exactly these points.

Why only offsets from b and e? A chop that splits at an interior point s recurses on spaces that s bounds. At that level, the checker computes the offsets again, with s as an anchor. So the required point is always a candidate.

Together, these two arguments give Theorem 4.1.
-->

---

# Complexity

<div class="grid gap-6 items-center" style="grid-template-columns: 1fr 470px">
<div>
<ul class="small">
  <li><Tex e="|CP(V, \varphi)|" /> is linear in the cars in the view, the segments, and <Tex e="|\varphi|" />.</li>
  <li>The checker explores <Tex e="O(|CP(V, \varphi)|^d)" /> observed spaces. Each costs <Tex e="O(|\varphi| \cdot |I_{V(E)}|)" />.</li>
  <li>Exponential in the chop depth <Tex e="d" />.</li>
  <li>Independent of the snapshot outside the view.</li>
</ul>
</div>
<div>
  <TimesChart />
  <div class="shot-cap">Median times from Table 1 of the paper (Apple M1 Max, one thread)</div>
</div>
</div>

<!--
[1:30 | total 19:00]

The size of the critical-point set is linear in the number of cars in the view, the segments that the view spans, and the size of phi. It is exponential in the chop depth d.

The algorithm explores order CP to the power d observed spaces. Each one costs order phi times the number of cars in the view. So the checker is exponential in the chop depth. But it does not depend on the snapshot outside the virtual view.

The evaluation confirms this. The scenario is a grid of eight roads with 40 cars. We vary the cars in the view from 2 to 10.

F1, re of E somewhere, stays below 0.1 seconds. The safety property F2 grows from 34 milliseconds at two cars to 1.5 seconds at ten. F3, a gap of more than 2 units ahead of E, grows from 0.07 to 1.0 seconds. F4 is almost the same as F3.

Nested chops are expensive when the checker cannot stop early. F6 has three nested chops and no witness. It takes 18 seconds at two cars and 4.2 minutes at ten.

With ten cars in view, F1 to F4 change by at most 2 percent between scenarios of 10, 40 and 80 cars. The checker carries into the view only the cars with a claim or a reservation in it.
-->

---
section: UMLSL-Sim
clicks: 3
---

# From UMLSL-Edit to UMLSL-Sim in one click

<div class="flow">
  <div v-click="1" class="step">
    <div class="pic" style="position: relative">
      <img class="shot" src="/shots/edit_main.png" style="width: 320px">
      <img class="shot menu" src="/shots/edit_file_menu.png">
    </div>
    <div class="lab"><span class="step-no">1</span>File ▸ Simulate in UMLSL-Sim…</div>
  </div>
  <div v-click="2" class="arrow">→</div>
  <div v-click="2" class="step">
    <div class="pic"><img class="shot" src="/shots/edit_simulate_prompt.png" style="width: 150px"></div>
    <div class="lab"><span class="step-no">2</span>Name the scenario</div>
  </div>
  <div v-click="3" class="arrow">→</div>
  <div v-click="3" class="step">
    <div class="pic"><img class="shot" src="/shots/sim_one_scene.png" style="width: 320px"></div>
    <div class="lab"><span class="step-no">3</span>UMLSL-Sim opens and runs it</div>
  </div>
</div>
<p class="shot-cap" style="margin-top: 10px">Sample scene <code>UMLSL-Edit/sample_scenes/sim_demo_one_crossing.json</code></p>

<style>
.flow { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
.step { display: flex; flex-direction: column; align-items: center; }
.pic { height: 215px; display: flex; align-items: center; }
.menu { position: absolute; left: 6px; top: 4px; width: 165px; box-shadow: 0 4px 12px rgba(0,0,0,0.35); }
.lab { display: flex; align-items: center; font-size: 13px; margin-top: 8px; }
.arrow { font-size: 26px; color: var(--kit-iceblue-70); }
</style>

<!--
[1:10 | total 20:10]

Now UMLSL-Sim. Scenarios that we create and analyse in UMLSL-Edit go directly to UMLSL-Sim. This is the one-crossing sample scene from before.

Click. In UMLSL-Edit, choose File, Simulate in UMLSL-Sim.

Click. Give the scenario a name.

Click. UMLSL-Sim opens with the scenario and starts to run it. The same five cars now drive in the simulator. The lines show their safety envelopes. The rings are their goals.

So we move from specification to simulation in one workflow.
-->

---
layout: picture
image: /shots/sim_two_scene.png
split: 50
fit: cover
imagePosition: 30% center
kitlogo: white
---

# UMLSL-Sim

<ul style="margin-top: 4px">
  <li>Discrete time: every car acts, then one frame passes.</li>
  <li>Safe controller: the set of all safe actions.</li>
  <li>Optimal controller: the highest safe acceleration. It moves to a lane that permits a higher one.</li>
  <li>Crossing claim: a lease that the car renews each frame.</li>
  <li class="safe"><b>150 episodes, 16 to 48 cars: no collision.</b></li>
</ul>

<!--
[1:15 | total 21:25]

This is the two-crossings scenario: eight roads that meet in 16 intersections.

The simulator takes a traffic snapshot as its start. It implements the action and time transitions of the model. In each frame, every car performs controller actions. When all cars have chosen, one frame passes. One frame is one time unit.

Each frame, the controllers of a car decide an acceleration and whether to change lanes. Lane-change safety comes from the controller of Hilscher et al. The maximum safe acceleration comes from a distance controller. It combines the cruise controller of Larsen et al. with the crossing controller of Schwammberger. The safe controller computes the set of all safe actions. The optimal controller picks the highest safe acceleration, and a lane change to a lane that permits a higher acceleration.

A car claims its path through a crossing automatically when it comes near. The claim is a lease, and the car renews it every frame. This keeps collision freedom, and it bounds the cyclic wait.

The result: no collision in any of the 150 episodes, with 16 to 48 cars. Traffic came to a complete stop in 4 of the 150 episodes, never below 32 cars.
-->

---

# Gymnasium environment and modes of use

<div class="grid gap-5 items-start" style="grid-template-columns: 1fr 440px">
<div>
<ul class="small">
  <li>The RL agent drives one car. The optimal controller drives the other cars.</li>
  <li>Action: an acceleration and a lane-change direction.</li>
  <li>An episode ends on a collision, a gridlock, or the step limit.</li>
  <li>Modules: algorithm, reward profile, observation model.</li>
  <li>Modes: train, evaluate or replay, hyperparameter search with Optuna.</li>
</ul>
</div>
<div>
  <img class="shot" src="/shots/sim_agent.png" style="width: 440px">
  <div class="shot-cap">Load trained model: a MaskablePPO agent with the shield drives the Maroon car</div>
</div>
</div>

<!--
[1:00 | total 22:25]

UMLSL-Sim is a Gymnasium environment. Gymnasium is the de facto standard Python interface for reinforcement learning.

At each step, the environment advances the simulation by one frame. The RL agent supplies an action for one agent car. Every other car is an NPC, driven by the optimal controller. So the agent learns among traffic that is safe by construction.

An action is an acceleration value and a lane-change direction. These are the same two decisions that the driving controllers make. The environment returns a numeric observation and a scalar reward. An episode ends on a collision, a gridlock, or a fixed step limit.

Training is modular. The algorithm comes from Stable-Baselines3: PPO, or MaskablePPO. Then there is the reward profile and the observation model. A new option needs only its interface and a registration.

The modes of use are training, evaluating or replaying a trained agent, and hyperparameter search with Optuna.

The screenshot shows the mode "Load trained model". A MaskablePPO agent with the shield drives the Maroon car. All other cars are NPCs.
-->

---

# Two ways to use the safe controller in training

<div class="grid gap-6 items-start" style="grid-template-columns: 1fr 230px">
<div>
  <SafetyMechanisms />
  <div class="grid grid-cols-2 gap-4 mt-3 small">
    <div class="box box-grey">
      <b>Reward profiles</b><br>
      initial-reward: + goal, − collision.<br>
      safety-aware-reward: also a penalty for each action that the safe controller rejects.
    </div>
    <div class="box box-safe">
      <b>Shield</b><br>
      Maximal braking and keeping the lane are always safe. So the mask is never empty.
    </div>
  </div>
</div>
<div>
  <img class="shot" src="/shots/sim_panel_shield.png" style="width: 230px">
  <div class="shot-cap">MaskablePPO turns the shield on</div>
</div>
</div>

<!--
[1:15 | total 23:40]

The safe controller can make RL training safe in two ways.

Left: reward shaping with PPO. The safety-aware reward profile penalises the agent after the step, when its action exceeded the safe acceleration or made a lane change that the controller rejects. It also rewards progress towards the goal and arrival at it, and it penalises collisions. The action space stays unconstrained. Unsafe actions remain reachable. The agent must trade the penalty against its objective, and the result has no safety guarantee.

Right: the shield with MaskablePPO. The verdict of the safe controller becomes a mask over the action space. The mask applies before the agent acts. So unsafe actions can neither be sampled nor contribute to the gradient. This holds at every point in training and for every policy. The reward can then talk about the objective alone. That is why we pair the shield with the initial reward profile.

Maximal braking and keeping the lane are always safe. So the mask is never empty.
-->

---

# Results: shield or reward

<table class="kit-table mt-1">
  <thead>
    <tr><th>Policy</th><th>unsafe acc. / 1000 steps</th><th>crash rate</th><th>goals</th><th>episode length</th></tr>
  </thead>
  <tbody>
    <tr><td>Random</td><td>247.0 ± 11.8</td><td class="unsafe"><b>0.74</b></td><td>28.3</td><td>305</td></tr>
    <tr><td>Random, shielded</td><td>0.0 ± 0.0</td><td class="safe"><b>0.00</b></td><td>31.0</td><td>494</td></tr>
    <tr><td>PPO, initial reward</td><td>222.6 ± 98.4</td><td class="unsafe"><b>0.43</b></td><td>20.3</td><td>379</td></tr>
    <tr><td>PPO, safety-aware reward</td><td>1.1 ± 1.1</td><td class="safe"><b>0.00</b></td><td>0.0</td><td>483</td></tr>
    <tr><td><b>MaskablePPO, shielded</b></td><td>0.0 ± 0.0</td><td class="safe"><b>0.00</b></td><td><b>41.0</b></td><td>487</td></tr>
  </tbody>
</table>
<p class="shot-cap">One-crossing scenario: 15 NPCs and one agent car. 100k training steps, three seeds, 30 evaluation episodes per seed.</p>

<ul class="small mt-3">
  <li>Shield: no rejected action in 88,280 steps. No crash in 90 episodes.</li>
  <li>Safety-aware reward: no crash, but almost no goals.</li>
</ul>

<!--
[1:00 | total 24:40]

We measured both mechanisms on the one-crossing scenario. It has 15 NPCs and one agent car. Each policy trains for 100k steps, which takes about four minutes. We use three seeds and the Stable-Baselines3 defaults. Two random policies, one with the shield and one without, are the reference.

The shield does what it promises. In 88,280 shielded steps, the agent took no action that the safe controller rejects. It did not crash once in 90 episodes. The shield alone takes the crash rate of the random policy from 0.74 to zero.

Reward shaping also cuts unsafe accelerations, to 1.1 per 1000 steps, and it never crashes. But the agent reaches almost no goals. It learns to drive very slowly and survive to the step limit.

With the shield, the reward can speak about the objective alone. The shielded agent reaches 41.0 goals. The unshielded agent with the same reward reaches 20.3 goals and crashes in 43 percent of its episodes.

A penalty makes an unsafe action expensive. The mask makes it unavailable.
-->

---
clicks: 3
---

# Back to UMLSL-Edit: re-analyse a snapshot

<div class="handoff">
  <div v-click="1" class="step">
    <img class="shot" src="/shots/sim_handoff.png" style="width: 400px">
    <div class="lab"><span class="step-no">1</span>Pause. Press Open in UMLSL-Edit.</div>
  </div>
  <div v-click="2" class="arrow">→</div>
  <div v-click="2" class="step">
    <img class="shot" src="/shots/edit_handoff.png" style="width: 430px">
    <div class="lab"><span class="step-no">2</span>UMLSL-Edit opens the snapshot.<span v-click="3">&nbsp;<span class="step-no">3</span>Check queries on it.</span></div>
  </div>
</div>

<style>
.handoff { display: flex; align-items: center; gap: 10px; margin-top: 6px; }
.handoff .step { display: flex; flex-direction: column; align-items: center; }
.handoff .lab { display: flex; align-items: center; font-size: 13px; margin-top: 8px; }
.handoff .arrow { font-size: 26px; color: var(--kit-iceblue-70); }
</style>

<!--
[1:00 | total 25:40]

The pipeline also runs in the other direction. Any simulation snapshot can go back to UMLSL-Edit for analysis.

Click. Here we paused the two-crossings run. We press Open in UMLSL-Edit. The simulator saves the paused state as a scenario.

Click. UMLSL-Edit opens that snapshot, with the same roads and cars.

Click. Now we can check UMLSL queries on it. Here we selected the car Apricot and added two queries from before. The safety query holds for Apricot. The gap query does not hold in this state.

So we can analyse the behaviour of the cars, and of trained agents, in the editor.
-->

---
section: Conclusion
---

# Conclusion and future work

<div class="grid gap-6 items-center" style="grid-template-columns: 430px 1fr">
<div>
  <Pipeline />
</div>
<div>
<ul class="small">
  <li>UMLSL-Edit: the first visual editor and model checker for UMLSL. Sound and complete.</li>
  <li>UMLSL-Sim: a Gymnasium environment. The safe controller works as a shield or as a reward.</li>
  <li>Scenarios pass between the tools in both directions.</li>
</ul>
<div class="muted small mt-4"><b>Next</b></div>
<ul class="small muted">
  <li>Faster critical points. Fewer gridlocks.</li>
  <li>Merging lanes, roundabouts, pedestrians, traffic signals. Timed (U)MLSL.</li>
</ul>
</div>
</div>

<!--
[1:15 | total 26:55]

To sum up. UMLSL-TK makes UMLSL executable.

UMLSL-Edit lets a user draw a traffic scenario and verify UMLSL formulas on it. The critical-point algorithm avoids any discretisation of the chopping point. We prove it sound and complete.

UMLSL-Sim runs these scenarios with implementations of the controllers of Hilscher et al., Schwammberger, and Larsen et al. Its Gymnasium environment uses the safe controller to shape the reward or as a safety shield. Scenarios pass between the tools. This closes the loop from specification to simulation and back. Both tools are modular, so users can adapt and extend them.

Next steps. In UMLSL-Edit, we want to make the critical-point approach more efficient. In UMLSL-Sim, we plan to improve the crossing claim and withdraw protocol. The aim is fewer gridlocks, and none under reasonable assumptions.

Beyond that, we plan merging and splitting lanes, roundabouts, pedestrians, and traffic signals. These need matching extensions to UMLSL and to the decision procedure. We also plan real-time properties: Timed (U)MLSL in the checker, and real-time simulation with a continuous action space in UMLSL-Sim.
-->

---

# Try UMLSL-TK

<div class="flex items-center justify-center gap-10" style="margin-top: 6px">
  <img src="/qr-umlsl-tk.png" style="width: 230px; height: 230px" alt="QR code to github.com/MASE-Group/umlsl-tk">
  <div>
    <p style="font-size: 20px"><b>github.com/MASE-Group/umlsl-tk</b></p>
    <p class="small muted">Open source. Python 3.11 or later. No separate GPU.</p>
    <p class="mt-6" style="font-size: 24px; font-family: var(--kit-font-title); font-weight: 600">Thank you. Questions?</p>
  </div>
</div>

<!--
[0:30 | total 27:25]

UMLSL-TK is open source and available on GitHub. Scan the code to get it. It runs on Python 3.11 or later, and it needs no separate GPU. The repository has the installation guide, the documentation, sample scenarios, and the benchmark scripts.

Thank you. I am happy to take your questions.
-->
