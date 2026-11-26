---
title: "Edit, Check, Simulate and Train: A Toolkit for UMLSL"
info: |
  SBMF 2026, Rio de Janeiro, Brazil, 03.12.2026.
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
exportFilename: opos-umlsl-tk-sbmf2026
kit:
  shortauthor: Hamarneh et al.
  shorttitle: "Edit, Check, Simulate and Train: A Toolkit for UMLSL"
  shortdate: 03.12.2026
  groupname: MASE group, KASTEL, KIT
layout: title
heading: "Edit, Check, Simulate and Train:\nA Toolkit for Urban Multi-Lane Spatial Logic"
authors: Qais Hamarneh, Nils Wenninghoff, Akhila Bairy, Mattis Bihler, Florian Portscher, Tim Kreuch, Tao Schmidt, Maike Schwammberger
event: SBMF 2026, Rio de Janeiro, Brazil
date: 03.12.2026
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

<div class="grid gap-8 items-center" style="grid-template-columns: 1fr 1fr; margin-top: 18px">
  <div>
    <MlslView bare />
  </div>
  <div>
    <img class="shot photo" src="/photos/intersection_from_above.jpg" alt="Bird's-eye view of a busy urban intersection">
    <div class="shot-cap">Photo: Bjankuloski06, Wikimedia Commons, CC BY 4.0</div>
  </div>
</div>

<style>
.photo { width: 100%; height: 300px; object-fit: cover; object-position: 50% 60%; }
</style>

<!--
[0:50 | total 1:10]

Autonomous and semi-automated driving functions promise safer and more comfortable mobility.

On the right is real traffic: an urban intersection from above. Research shows that test drives in such traffic alone are not sufficient to prove safety. So we also need other means, such as formal specification and verification. Formal methods need tool support to check system properties in a systematic way.

On the left is the abstract model in which we specify and verify: lanes, cars, and the space that they reserve and claim.

A gap remains between abstract spatial logics like this one and environments that we can execute and train in. To bridge it is not trivial. Tools must handle run-time situations and corner cases. They must also work with modern machine learning frameworks.

UMLSL-TK bridges this gap for UMLSL.
-->

---
section: Background
---

# MLSL: the highway model

<div class="mx-auto" style="width: 680px; margin-top: 10px">
  <MlslView />
</div>

<!--
[1:15 | total 2:25]

UMLSL extends the highway traffic model and the Multi-Lane Spatial Logic, MLSL, of Hilscher et al. So we start on the highway.

Lanes are discrete. Positions along the lanes are continuous.

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

Atoms: $\mathit{re}(C)$, &emsp; $\mathit{cl}(C)$, &emsp; $\ell \sim k$

Operators: $\neg\varphi$, &emsp; $\varphi_1 \land \varphi_2$, &emsp; $\varphi_1 \lor \varphi_2$, &emsp; $\exists c\colon \varphi$

Somewhere: $\langle\varphi\rangle \equiv \begin{array}{c}\mathit{true}\\ \mathit{true}\frown\varphi\frown\mathit{true}\\ \mathit{true}\end{array}$

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

The horizontal chop splits the space at a point r along the lanes. phi 1 must hold before r, and phi 2 after r. The vertical chop splits the space at a lane border. phi 1 holds below, and phi 2 holds above. We write it as phi 2 stacked above phi 1.

The atoms re of C and cl of C need exactly one lane. They say that car C reserves, or claims, all of that space. The symbol l is the length of the space, and we compare it with constants.

On top of the atoms we have the Boolean operators and the existential quantifier over cars.

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
  <li>Virtual lane: one path through the crossing.</li>
  <li>New atom <Tex e="\mathit{cs}" />: the space lies in an intersection.</li>
  <li>Example: <Tex e="\langle \mathit{re}(E) \frown \mathit{free}^{>d} \frown \mathit{cs}\rangle" /></li>
</ul>
<p class="muted small" style="margin: 6px 0 0 1.05em"><Tex e="\mathit{free}^{>d} \equiv \mathit{free} \land \ell > d" /></p>
</div>
</div>

<!--
[1:15 | total 6:10]

Schwammberger extends the model and the logic to urban traffic. The result is UMLSL.

The road network has vertical and horizontal roads, their lanes, and intersections. Here the horizontal road has one lane to the left and two to the right. The vertical road has one lane down and two up. The network forms a graph. The nodes are lane segments, the parts of a lane between two intersections, and crossing segments, here c0 to c8. Directed edges connect segments along the driving direction. Undirected edges connect adjacent lane segments.

Car D comes down and turns right. It reserves its whole path through the crossing, plus its own length beyond it.

Far from an intersection, each virtual lane is one lane segment. Near an intersection, a virtual lane is a sequence of lane and crossing segments. It is one possible path through the crossing. The view of E runs into the crossing.

UMLSL adds the atom cs. It says that the observed space lies on crossing segments.

An example formula: re of E, chop free space longer than d, chop cs. It asks whether E reserves space, then more than d units of free space follow, and then the intersection. Whether it holds depends on d and on the length of that free space.
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
  <img class="shot" src="/shots/edit_car.png" style="width: 108px">
  <div class="shot-cap">Car dialog</div>
  <ul class="mt-3 small">
    <li>Add roads. The tool creates the crossings.</li>
    <li>Place cars: lane, position, speed, acceleration, next turn.</li>
    <li>Move cars by drag and drop.</li>
    <li>Select a car. Its virtual view appears.</li>
  </ul>
</div>
</div>

<!--
[1:30 | total 8:55]

UMLSL-Edit is the first tool. It is a visual editor and model checker for UMLSL. The user builds a scenario on an infinite canvas.

This is a sample scene with one crossing and five cars. We simulate the same scene later.

The user adds vertical or horizontal roads. Each road can have any number of lanes in both directions, in right-hand traffic. Where two roads intersect, the tool creates the lane segments and crossing segments.

Then the user places cars. Each car has a lane, a position, a speed, and an acceleration. A car can also claim or reserve an adjacent lane. The user gives the next turn of the car. From it, the tool computes the path through the crossing segments. The tool reserves space from the size and the safety envelope of the car.

Cars move by drag and drop. When the user selects a car, the tool shows its virtual view.
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
  <li>Type the query in a LaTeX-like syntax. The tool shows it in mathematical notation.</li>
  <li>The checker decides each query in the view of its car.</li>
</ul>
</div>
</div>

<!--
[1:30 | total 10:25]

Each query belongs to one ego car. The checker evaluates it in the virtual view of that car.

Queries use a LaTeX-like syntax. The tool documents the syntax in a help dialog. It parses each query and shows it in mathematical notation.

Here are three queries. The first one is the safety property for car A. It holds. The second one asks for a gap of more than 2 units ahead of the reservation of E. It holds too. The third one is re of E chop cs. It does not hold, because space separates E from the crossing. The tool marks a false query in red.

UMLSL-Edit decides formulas in a separate process. So the editor stays responsive while the checker works.
-->

---
section: Model checking
clicks: 6
---

# Model checking: a recursive descent

<p class="muted small" style="margin-top:-6px">Decide <Tex e="TS, V(E) \models \varphi" />. Start with the observed space <Tex e="V(E)" />.</p>

<div class="rules">
  <div v-click="1" class="rule"><SpaceGlyph kind="atom" /><span><b>Atom:</b> test <Tex e="[b,e] \subseteq \mathit{CS}_l, \mathit{RE}_l(C), \mathit{CL}_l(C)" />. False if <Tex e="|L| \neq 1" />.</span></div>
  <div v-click="2" class="rule"><SpaceGlyph kind="same" /><span><b><Tex e="\neg, \land, \lor" />:</b> recurse on the same space.</span></div>
  <div v-click="3" class="rule"><SpaceGlyph kind="cars" /><span><b><Tex e="\exists c" />:</b> one call for each car in the view. The set is finite.</span></div>
  <div v-click="4" class="rule"><SpaceGlyph kind="vchop" /><span><b>Vertical chop:</b> try each lane border. There are finitely many.</span></div>
  <div v-click="5" class="rule"><SpaceGlyph kind="hchop" /><span><b>Horizontal chop:</b> the chopping point <Tex e="r" /> ranges over the continuous interval <Tex e="[b, e]" />. Which points to try?</span></div>
</div>

<div v-click="6" class="box box-safe cp-box">
  <div class="box-title">Critical Points Algorithm</div>
  <span class="small">A finite set of candidates for <Tex e="r" />, with no discretisation. Sound and complete. A pixel grid would be sound, but incomplete and highly inefficient.</span>
</div>

<style>
.rules { display: flex; flex-direction: column; gap: 12px; margin-top: 10px; }
.rule { display: flex; align-items: center; gap: 14px; }
.cp-box { margin-top: 18px; }
</style>

<!--
[1:50 | total 12:15]

Now the main part: the model checker.

Input: a traffic snapshot TS, an ego car E, and a query phi. The checker decides whether phi holds over the virtual view of E. It follows the semantics of UMLSL.

The check is a recursive descent over the structure of phi. It carries the current observed space. The first call gets the whole virtual view.

Click. An atom is decided directly. The checker tests whether the interval is inside a crossing segment, a reservation, or a claim on the one lane. If the space has more than one lane, the atom fails at once.

Click. Boolean connectives recurse on the same space.

Click. The quantifier ranges over the cars in the view. That set is finite, so there is one recursive call for each car.

Click. The vertical chop tries each lane border. There are finitely many.

Click. Only the chop operators make the space smaller. And the horizontal chop has a problem. All UMLSL operators range over finite sets, with one exception: the chopping point r of the horizontal chop ranges over the continuous interval from b to e.

Click. One idea is to discretise this interval, for example along the pixel grid of the visual editor. The result is sound but incomplete, because all witnesses can lie between two grid points. It is also highly inefficient. We use the Critical Points Algorithm instead. The set of candidates is finite without any discretisation, and we prove that the procedure is sound and complete.
-->

---
clicks: 4
---

# Critical points $CP(V, \varphi)$

<p class="muted small" style="margin-top:-6px">Example on one lane: <Tex e="\varphi = (\mathit{re}(E) \land \ell \geq 1) \frown (\ell > 2 \land \mathit{free}) \frown \mathit{cs}" />, so <Tex e="\mathit{Constants}(\varphi) = \{1, 2\}" /> and <Tex e="d = 2" />.</p>

<div class="grid gap-5 items-center" style="grid-template-columns: 540px 1fr">
<div>
  <CriticalPoints :step="$clicks" />
</div>
<div class="small legend">
  <p v-click="1"><PointMark kind="base" /><b>Base:</b> <Tex e="b" />, <Tex e="e" />, and each endpoint of a reservation, claim or segment</p>
  <p v-click="2"><PointMark kind="off" /><b>Off:</b> <Tex e="b \pm s" />, <Tex e="e \pm s" />, where <Tex e="s" /> sums at most <Tex e="d" /> constants of <Tex e="\mathit{Constants}(\varphi)" />: here <Tex e="s \in \{1, 2, 3, 4\}" /></p>
  <p v-click="3"><PointMark kind="mid" /><b>Mid:</b> one midpoint in each open gap</p>
  <p v-click="4"><b>Try each point as <Tex e="r" />.</b> Stop when both sides of the chop hold.</p>
</div>
</div>

<style>
.legend p { margin: 0 0 12px 0; }
</style>

<!--
[2:15 | total 14:30]

Here is the construction on a small example. One lane, an interval from b to e. Car E reserves the start of the interval. A crossing segment lies further ahead. The formula is: E reserves a space of length at least 1, chop, a free space longer than 2, chop, a crossing segment. It is the example from the urban model. It has two constants, 1 and 2, and two nested horizontal chops. So d is 2.

Click. First, the base points. These are b, e, and every endpoint of a reservation, a claim, or a segment inside the interval. We take them over all lanes in the space and all cars in the view. An atom can change its truth value only at these points.

Click. Second, the offsets, drawn as stars. Constants of phi is the set of constants k in length comparisons in phi. d is the nesting depth of horizontal chops. We add b plus or minus s and e plus or minus s, where s is a sum of at most d constants, with repetition. With d equal to 2, s is 1, 2, 1 plus 1, 1 plus 2, or 2 plus 2. That is 1, 2, 3 or 4. So we get b plus 1 to b plus 4, and e minus 4 to e minus 1. The other points fall outside the interval.

Click. Third, the midpoints. Between each pair of adjacent points so far, we add one representative. We take the midpoint.

The union of the three sets is CP of V and phi.

Click. The checker tries the elements of CP as chopping points. It succeeds as soon as one point splits the space so that both operands hold. The outer chop splits at the start of the crossing segment: to the right lies cs. On the left part, the checker computes the critical points again, and the inner chop splits at the end of the reservation of E. There, E reserves the space, and it is longer than 1. Between the two points, the space is free and longer than 2.
-->

---

# Why the procedure is sound and complete

<div class="box box-grey mb-6">
  <b>Theorem 4.1.</b> The model checker returns true if and only if <Tex e="TS, V(E) \models \varphi" />.
</div>

<div class="box-title">Sound</div>
<p>Each candidate lies in <Tex e="[b, e]" />. So a positive answer always comes with a witness.</p>

<div class="box-title mt-8">Complete</div>
<p class="muted">In two steps, on the next two slides:</p>
<ol class="small muted">
  <li>formulas without length comparisons: cells between base points,</li>
  <li>length comparisons <Tex e="\ell \sim k" />: the offsets.</li>
</ol>

<!--
[0:50 | total 15:20]

Theorem 4.1 says that the checker returns true if and only if the formula holds. Here is the intuition. The full proof is in the appendix of the paper.

Soundness is simple. Every chopping candidate lies in the interval from b to e. So a positive answer always shows a real witness. This holds for every formula.

Completeness takes two steps. First, formulas without length comparisons. Then we add the length comparisons.
-->

---

# Completeness (1/2): cells between base points

<p class="muted small" style="margin-top:-6px">Step 1 of the completeness argument: formulas without length comparisons.</p>

<div class="mx-auto" style="width: 640px; margin-top: 8px">
  <CellsDiagram />
</div>

<ul class="small mt-2">
  <li><Tex e="\mathit{CS}_l" />, <Tex e="\mathit{RE}_l(C)" /> and <Tex e="\mathit{CL}_l(C)" /> change membership only at base points. So each is constant on each cell.</li>
  <li>Base points plus midpoints hold one representative of each cell.</li>
</ul>

<!--
[1:00 | total 16:20]

For completeness, first take formulas without length comparisons. The intervals of crossing segments, reservations and claims change their membership only at base points. So each of them is constant on each cell. A cell is either one base point or one open interval between two adjacent base points.

So whether a formula holds depends on b and e only through the cells that they lie in. A witness s of a chop can move to the representative of its cell. The midpoint m is in the same cell, so m is a witness too. And the base points plus the midpoints contain one representative for each cell.

This is not yet the full argument. Length comparisons need one more step.
-->

---

# Completeness (2/2): length comparisons

<p class="muted small" style="margin-top:-6px">Step 2 of the completeness argument: add the comparisons <Tex e="\ell \sim k" />.</p>

<div class="mx-auto" style="width: 600px">
  <OffsetsDiagram />
</div>

<ul class="small mt-1">
  <li>A comparison <Tex e="\ell \sim k" /> cuts the cells again, at distance <Tex e="k" /> from an anchor.</li>
  <li><Tex e="\mathit{Off}(V, \varphi) = \{a \pm s \mid a \in \{b, e\},\ s \in S_d(\varphi)\} \cap (b, e)" />, where <Tex e="S_d(\varphi)" /> holds <b>every</b> sum of up to <Tex e="d" /> constants of <Tex e="\mathit{Constants}(\varphi)" />, with repetition.</li>
  <li>Here <Tex e="\mathit{Constants}(\varphi) = \{1, 2\}" /> and <Tex e="d = 2" />, so <Tex e="S_2(\varphi) = \{1, 2, 3, 4\}" />.</li>
  <li>Offsets start from <Tex e="b" /> and <Tex e="e" /> only. A split point <Tex e="r" /> is an anchor one level down.</li>
</ul>

<!--
[1:15 | total 17:35]

This is the second step of the completeness argument. Now add length comparisons. A comparison l similar to k depends only on the length of the space. So it refines the cells by the constant k.

A chain of d nested chops can add up to d of these constants. So the offsets contain every sum of up to d constants, with repetition, measured from b and from e. In the example, the constants are 1 and 2, and d is 2. The sums are 1, 2, 1 plus 1, 1 plus 2 and 2 plus 2. That gives offsets at distance 1, 2, 3 and 4 from b and from e.

Why only offsets from b and e? A chop that splits at an interior point r recurses on spaces that r bounds. At that level, the checker computes the offsets again, with r as an anchor. So the required point is always a candidate.

Together, the two steps give Theorem 4.1.
-->

---

# Complexity

<div class="grid gap-6 items-center" style="grid-template-columns: 1fr 470px">
<div>
<ul class="small">
  <li>The checker explores <Tex e="O(|CP(V, \varphi)|^d)" /> observed spaces.
    <ul class="small">
      <li>Each costs <Tex e="O(|\varphi| \cdot |Cars_{V(E)}|)" />.</li>
      <li>linear in the cars in the view, the segments, and</li>
      <li>exponential in the chop depth <Tex e="d" />.</li>
    </ul>
  </li>
  <li>Independent of the traffic outside the view.</li>
</ul>
</div>
<div>
  <TimesChart />
  <div class="shot-cap">Median times, Apple M1 Max, Python 3.14, one thread</div>
</div>
</div>

<!--
[1:30 | total 19:05]

The algorithm explores order CP to the power d observed spaces. Each one costs order phi times the number of cars in the view.

The size of the critical-point set is linear in the number of cars in the view and the segments that the view spans. It is exponential in the chop depth d. So the checker is exponential in the chop depth. But it does not depend on the traffic outside the virtual view.

The evaluation confirms this. The scenario is a grid of eight roads with 40 cars. We vary the cars in the view from 2 to 10.

F1, re of E somewhere, stays below 20 milliseconds. The safety property F2 grows from 9 milliseconds at two cars to 0.36 seconds at ten. F3, a gap of more than 2 units ahead of E, grows from 21 milliseconds to 0.30 seconds. F4 is almost the same as F3.

Nested chops are expensive when the checker cannot stop early. F6 has three nested chops and no witness. It takes 1.2 seconds at two cars and 13 seconds at ten.

With ten cars in view, F2 to F4 change by at most 6 percent between scenarios of 10, 40 and 80 cars. F1 grows by about 2 milliseconds, from 17 to 19. The checker carries into the view only the cars with a claim or a reservation in it.
-->

---
section: UMLSL-Sim
clicks: 1
---

# From UMLSL-Edit to UMLSL-Sim in one click

<div class="flow">
  <div class="step">
    <div class="pic" style="position: relative">
      <img class="shot" src="/shots/edit_main.png" style="width: 380px">
      <img class="shot menu" src="/shots/edit_file_menu.png">
    </div>
    <div class="lab"><span class="step-no">1</span>File ▸ Simulate in UMLSL-Sim…</div>
  </div>
  <div v-click="1" class="arrow">→</div>
  <div v-click="1" class="step">
    <div class="pic"><img class="shot" src="/shots/sim_one_frame0.png" style="width: 380px"></div>
    <div class="lab"><span class="step-no">2</span>UMLSL-Sim opens and runs it</div>
  </div>
</div>
<p class="shot-cap" style="margin-top: 10px">Sample scene <code>UMLSL-Edit/sample_scenes/sim_demo_one_crossing.json</code></p>

<style>
.flow { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 4px; }
.step { display: flex; flex-direction: column; align-items: center; }
.pic { height: 255px; display: flex; align-items: center; }
.menu { position: absolute; left: 6px; top: 4px; width: 190px; box-shadow: 0 4px 12px rgba(0,0,0,0.35); }
.lab { display: flex; align-items: center; font-size: 13px; margin-top: 8px; }
.arrow { font-size: 26px; color: var(--kit-iceblue-70); }
</style>

<!--
[1:00 | total 20:05]

Now UMLSL-Sim. Scenarios that we create and analyse in UMLSL-Edit go directly to UMLSL-Sim. This is the one-crossing sample scene from before.

In UMLSL-Edit, choose File, Simulate in UMLSL-Sim.

Click. UMLSL-Sim opens with the scenario and starts to run it. The same five cars, at the same positions, now drive in the simulator. The lines show their safety envelopes. The rings are their goals.

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
  <li>Traffic simulation</li>
  <li>Safe Training Controller: the set of all safe actions.</li>
  <li>Safe NPC Controller: the highest safe acceleration. It moves to a lane that permits a higher one.</li>
</ul>

<!--
[1:00 | total 21:05]

This is the two-crossings scenario: eight roads that meet in 16 intersections.

UMLSL-Sim is a traffic simulation. It takes a traffic snapshot as its start. It implements the action and time transitions of the model. In each frame, every car performs controller actions. When all cars have chosen, one frame passes. One frame is one time unit.

Each frame, the controllers of a car decide an acceleration and whether to change lanes. Lane-change safety comes from the controller of Hilscher et al. The maximum safe acceleration comes from a distance controller. It combines the cruise controller of Larsen et al. with the crossing controller of Schwammberger.

The Safe Training Controller computes the set of all safe actions. We use it in training. The Safe NPC Controller drives the other cars. It picks the highest safe acceleration, and a lane change to a lane that permits a higher acceleration.
-->

---

# Gymnasium environment and modes of use

<div class="grid gap-6 items-start" style="grid-template-columns: 1fr 440px">
<div class="gym">
  <div class="gym-row">
    <div class="gym-k">Agents</div>
    <div>Reinforcement Learning (RL) agent(s) drive some cars.<br>NPC Controllers drive the others.</div>
  </div>
  <div class="gym-row">
    <div class="gym-k">Episode</div>
    <div>Ends on a collision, a gridlock, or the step limit.</div>
  </div>
  <div class="gym-row">
    <div class="gym-k">Modules</div>
    <div class="chips"><span>RL algorithm</span><span>reward profile</span><span>observation model</span></div>
  </div>
  <div class="gym-row">
    <div class="gym-k">Modes</div>
    <div class="chips modes">
      <span><b>1</b>hyperparameter search with Optuna</span>
      <span><b>2</b>train</span>
      <span><b>3</b>evaluate</span>
      <span><b>4</b>simulate</span>
    </div>
  </div>
</div>
<div>
  <img class="shot" src="/shots/sim_agent.png" style="width: 440px">
  <div class="shot-cap">Load trained model: a MaskablePPO agent with the shield drives the white car</div>
</div>
</div>

<style>
.gym { font-size: 15px; line-height: 1.35; margin-top: 4px; }
.gym-row { display: grid; grid-template-columns: 78px 1fr; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--kit-iceblue-30); }
.gym-row:first-child { border-top: 2px solid var(--kit-royalblue); }
.gym-k { font-family: var(--kit-font-title); font-weight: 600; color: var(--kit-green); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chips span { background: var(--kit-iceblue-15); border: 1px solid var(--kit-iceblue-50); padding: 2px 9px; font-size: 14px; }
.chips.modes { flex-direction: column; align-items: flex-start; }
.chips.modes b { display: inline-flex; align-items: center; justify-content: center; width: 17px; height: 17px; margin-right: 7px;
  border-radius: 50%; background: var(--kit-royalblue); color: #fff; font-size: 11px; vertical-align: 1px; }
</style>

<!--
[1:00 | total 22:05]

UMLSL-Sim is a Gymnasium environment. Gymnasium is the de facto standard Python interface for reinforcement learning.

At each step, the environment advances the simulation by one frame. The RL agent supplies the actions for its agent cars. Every other car is an NPC, driven by the Safe NPC Controller. So the agent learns among traffic that is safe by construction.

An action is an acceleration value and a lane-change direction. These are the same two decisions that the driving controllers make. The environment returns a numeric observation and a scalar reward. An episode ends on a collision, a gridlock, or a fixed step limit.

Training is modular. The algorithm comes from Stable-Baselines3: PPO, or MaskablePPO. Then there is the reward profile and the observation model. A new option needs only its interface and a registration.

The four modes of use are hyperparameter search with Optuna, training, evaluating a trained agent, and simulating.

The screenshot shows the mode "Load trained model". A MaskablePPO agent with the shield drives the white car. All other cars are NPCs.
-->

---

# Crossing claim: a lease

<p class="muted small" style="margin-top:-6px">A car claims its path through a crossing automatically when it comes near. It holds the claim as a lease.</p>

<div class="mx-auto" style="width: 800px; margin-top: 2px">
  <LeaseTimeline />
</div>

<div class="grid grid-cols-3 gap-4 mt-2 lease-boxes">
  <div class="box box-grey">
    <b>Lease</b><br>
    Cars cross in the order they claim. A moving car renews its claim each frame. After 4 frames without progress, the claim moves back. After 12, it is withdrawn.
  </div>
  <div class="box box-safe">
    <b>Safety unchanged</b><br>
    A car still enters a crossing segment only with a reservation of it. At most one car holds that reservation.
  </div>
  <div class="box box-grey">
    <b>Bounded wait</b><br>
    A stalled car holds a crossing for at most 12 frames. So a ring of waiting cars always breaks. Gridlock is rarer, but still possible.
  </div>
</div>

<style>
.lease-boxes { font-size: 13px; line-height: 1.3; }
</style>

<!--
[1:15 | total 23:20]

One more change in UMLSL-Sim concerns the crossing claim.

A car claims its path through a crossing automatically, once it comes within a threshold distance of the intersection. So the simulator, not the controller, performs the actions cc and wd cc. Cars cross in the order in which they claim: first come, first served.

The claim is a lease, not a permanent grant. The car renews it in every frame in which it makes progress. In the timeline, A claims first and moves. Then A stalls. B claimed after A, so B waits. After 4 frames without progress, A's claim moves behind the cars that still approach normally. Now B is first and enters. After 12 frames without progress, A's claim is withdrawn. A claims again later, at the back of the queue.

This does not affect the collision freedom proof. A car still enters a crossing segment only while it holds a reservation of it. And at most one car holds a reservation at a time.

What the lease buys is a bound on the cyclic wait. A car that cannot move never holds an intersection closed for more than 12 frames. So the claim that closes a ring of cars, each waiting on the next, is always released in bounded time. This does not guarantee gridlock freedom. In our runs, gridlock happened in 4 of 150 episodes with the lease, and in 8 of 50 without it.
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
[1:15 | total 24:35]

The Safe Training Controller can make RL training safe in two ways.

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
[1:00 | total 25:35]

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
[1:00 | total 26:35]

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

<div class="grid gap-6" style="grid-template-columns: 430px 1fr">
<div class="left-col">
  <Pipeline />
  <div class="repo">
    <img src="/qr-umlsl-tk.png" alt="QR code to github.com/MASE-Group/umlsl-tk">
    <div>
      <p class="repo-url"><b>github.com/MASE-Group/umlsl-tk</b></p>
      <p class="small muted">Open source. Python 3.11 or later.</p>
    </div>
  </div>
</div>
<div>
<ul class="small">
  <li><b>UMLSL-Edit</b>: the first visual editor and model checker for UMLSL. Sound and complete.</li>
  <li><b>UMLSL-Sim</b>: a Gymnasium environment. The safe controller works as a shield or as a reward.</li>
  <li>Scenarios pass between the tools in both directions.</li>
</ul>
<div class="muted small mt-4"><b>Next Steps</b></div>
<ul class="small muted">
  <li><b>More traffic scenarios</b>: Merging lanes, roundabouts, traffic signals.</li>
  <li><b>Optimizations</b>: Faster model checking, avoiding gridlocks.</li>
  <li><b>Real-time UMLSL and simulation</b></li>
</ul>
</div>
</div>

<style>
.left-col { display: flex; flex-direction: column; height: 360px; }
.repo { margin-top: auto; display: flex; align-items: center; gap: 14px; }
.repo img { width: 118px; height: 118px; flex: none; }
.repo-url { font-size: 16px; margin: 0 0 4px 0; }
</style>

<!--
[1:30 | total 28:05]

To sum up. UMLSL-TK makes UMLSL executable.

UMLSL-Edit lets a user draw a traffic scenario and verify UMLSL formulas on it. The Critical Points Algorithm avoids any discretisation of the chopping point. We prove it sound and complete.

UMLSL-Sim runs these scenarios with implementations of the controllers of Hilscher et al., Schwammberger, and Larsen et al. Its Gymnasium environment uses the safe controller to shape the reward or as a safety shield. Scenarios pass between the tools. This closes the loop from specification to simulation and back. Both tools are modular, so users can adapt and extend them.

Next steps. In UMLSL-Edit, we want to make the critical-point approach more efficient. In UMLSL-Sim, we plan to improve the crossing claim and withdraw protocol. The aim is fewer gridlocks, and none under reasonable assumptions.

Beyond that, we plan merging and splitting lanes, roundabouts, pedestrians, and traffic signals. These need matching extensions to UMLSL and to the decision procedure. We also plan real-time properties: Timed (U)MLSL in the checker, and real-time simulation with a continuous action space in UMLSL-Sim.

UMLSL-TK is open source and available on GitHub. Scan the code to get it. It runs on Python 3.11 or later. The repository has the installation guide, the documentation, sample scenarios, and the benchmark scripts.

Thank you. I am happy to take your questions.
-->

---
section: Backup
---

# Backup: MLSL and UMLSL papers

<div class="refs">
  <div class="box-title">MLSL: the highway model and its logic</div>
  <p class="small">M. Hilscher, S. Linker, E.-R. Olderog, A. P. Ravn. <i>An abstract model for proving safety of multi-lane traffic manoeuvres.</i> ICFEM 2011, LNCS 6991, pp. 404–419. Springer, 2011. <span class="muted">doi:10.1007/978-3-642-24559-6_28</span></p>

  <div class="box-title mt-5">UMLSL: the urban model and its logic</div>
  <p class="small">M. Schwammberger. <i>An abstract model for proving safety of autonomous urban traffic.</i> Theoretical Computer Science 744, pp. 143–169, 2018. <span class="muted">doi:10.1016/j.tcs.2018.05.028</span></p>

  <div class="box-title mt-5">Further work on (U)MLSL</div>
  <ul class="tiny">
    <li>S. Linker, M. Hilscher. <i>Proof theory of a multi-lane spatial logic.</i> LMCS 11(3), 2015.</li>
    <li>M. Schwammberger. <i>Introducing liveness into multi-lane spatial logic lane change controllers using UPPAAL.</i> SCAV 2018, EPTCS 269, pp. 17–31.</li>
    <li>C. Bischopink, M. Schwammberger. <i>Verification of fair controllers for urban traffic manoeuvres at intersections.</i> FM 2019 Workshops, LNCS 12232, pp. 249–264.</li>
    <li>M. Schwammberger, G. V. Alves. <i>Extending urban multi-lane spatial logic to formalise road junction rules.</i> FMAS 2021, EPTCS 348, pp. 1–19.</li>
  </ul>
</div>

<style>
.refs p { margin: 0 0 4px 0; }
</style>

<!--
Backup. The two papers that define the models and logics behind UMLSL-TK.

MLSL and the highway model with the lane-change controller: Hilscher, Linker, Olderog and Ravn, ICFEM 2011.

UMLSL and the urban model with the crossing controller: Schwammberger, Theoretical Computer Science 2018.

Below are related results: the proof theory of MLSL, liveness and fairness of the controllers, and junction rules.
-->

---

# Backup: UMLSL syntax

<div class="box box-grey" style="font-size: 19px; padding: 12px 16px">
  <Tex e="\varphi ::= \mathit{cs} \mid \mathit{true} \mid \mathit{re}(C) \mid \mathit{cl}(C) \mid \ell \sim k \mid C = C' \mid \neg\varphi \mid \varphi \land \varphi \mid \varphi \lor \varphi \mid \exists c \in I\colon \varphi' \mid \varphi_1 \frown \varphi_2 \mid \begin{array}{c}\varphi_2\\ \varphi_1\end{array}" />
</div>

<ul class="small mt-4">
  <li><Tex e="\mathit{cs}" /> (crossing segment): the observed space lies on crossing segments, i.e. within an intersection.</li>
  <li><Tex e="\mathit{re}(C)" />, <Tex e="\mathit{cl}(C)" />: car <Tex e="C" /> reserves, respectively claims, all of the observed space.</li>
  <li><Tex e="C, C' \in I" /> are car identifiers. <Tex e="\ell" /> is the length of the observed space, <Tex e="k \in \mathbb{R}" /> a constant, and <Tex e="{\sim} \in \{<, \leq, =, \geq, >\}" />.</li>
  <li><Tex e="\varphi_1 \frown \varphi_2" /> is the horizontal chop. <Tex e="\begin{array}{c}\varphi_2\\ \varphi_1\end{array}" /> is the vertical chop.</li>
  <li>Lengths are compared with constants, and car identifiers with each other. The two sorts never mix.</li>
  <li><Tex e="\forall" /> and <Tex e="\Rightarrow" /> are the usual abbreviations.</li>
</ul>

<p class="tiny muted mt-3">A slight variant of the syntax of Schwammberger (2018), without additional variables. Both syntaxes have the same expressivity.</p>

<!--
Backup. The full syntax of UMLSL as we use it in the paper and in UMLSL-Edit.

The atoms are cs, true, re of C, cl of C, length comparisons and the equality of car identifiers. Then the Boolean connectives, the existential quantifier over cars, and the two chops.

This is a slight variant of the syntax of Schwammberger. It avoids additional variables. Both syntaxes have the same expressivity.
-->

---

# Backup: UMLSL semantics

<p class="muted small" style="margin-top:-6px">Observed space <Tex e="V = (L, [b, e])" /> within the virtual view <Tex e="V(E)" />. <Tex e="\mathit{RE}_l(C)" />, <Tex e="\mathit{CL}_l(C)" />, <Tex e="\mathit{CS}_l" />: positions on lane <Tex e="l" /> that <Tex e="C" /> reserves, that <Tex e="C" /> claims, that lie on crossing segments.</p>

<table class="sem">
  <tbody>
    <tr><td><Tex e="TS, V \models \mathit{cs}" /></td><td>iff</td><td><Tex e="L = \{l\}" /> and <Tex e="[b, e] \subseteq \mathit{CS}_l" /></td></tr>
    <tr><td><Tex e="TS, V \models \mathit{re}(C)" /></td><td>iff</td><td><Tex e="L = \{l\}" /> and <Tex e="[b, e] \subseteq \mathit{RE}_l(C)" /></td></tr>
    <tr><td><Tex e="TS, V \models \mathit{cl}(C)" /></td><td>iff</td><td><Tex e="L = \{l\}" /> and <Tex e="[b, e] \subseteq \mathit{CL}_l(C)" /></td></tr>
    <tr><td><Tex e="TS, V \models \ell \sim k" /></td><td>iff</td><td><Tex e="e - b \sim k" /></td></tr>
    <tr><td><Tex e="TS, V \models C = C'" /></td><td>iff</td><td><Tex e="C" /> and <Tex e="C'" /> are the same car identifier</td></tr>
    <tr><td><Tex e="TS, V \models \exists c \in I\colon \varphi'" /></td><td>iff</td><td><Tex e="TS, V \models \varphi'[C/c]" /> for some <Tex e="C \in I_{V(E)}" /></td></tr>
    <tr><td><Tex e="TS, V \models \varphi_1 \frown \varphi_2" /></td><td>iff</td><td>for some <Tex e="r \in [b, e]" />: <Tex e="TS, (L, [b, r]) \models \varphi_1" /> and <Tex e="TS, (L, [r, e]) \models \varphi_2" /></td></tr>
    <tr><td><Tex e="TS, V \models \begin{array}{c}\varphi_2\\ \varphi_1\end{array}" /></td><td>iff</td><td><Tex e="L = \{i, \dots, j\}" /> and for some <Tex e="i - 1 \leq k \leq j" />: <Tex e="TS, (\{i, \dots, k\}, [b, e]) \models \varphi_1" /> and <Tex e="TS, (\{k+1, \dots, j\}, [b, e]) \models \varphi_2" /></td></tr>
  </tbody>
</table>

<p class="tiny muted mt-2"><Tex e="\mathit{true}" />, <Tex e="\neg" />, <Tex e="\land" />, <Tex e="\lor" /> as usual. A formula holds for the ego car <Tex e="E" /> iff <Tex e="TS, V(E) \models \varphi" />, i.e. over the whole virtual view.</p>

<style>
.sem { border-collapse: collapse; font-size: 13.5px; margin-top: 6px; }
.sem td { padding: 3px 8px; border-bottom: 1px solid var(--kit-iceblue-30); vertical-align: middle; }
.sem td:nth-child(2) { color: var(--kit-iceblue-70); }
.sem .katex { font-size: 1em; }
</style>

<!--
Backup. The satisfaction relation of UMLSL, as in Figure 3 of the paper.

The atoms need exactly one lane. cs, re and cl test whether the interval lies within the crossing segments, the reservation, or the claim on that lane. A length comparison tests e minus b. The quantifier ranges only over the cars in the view.

The horizontal chop splits at a point r in the interval. The vertical chop splits at a lane border. It admits k equal to i minus 1 and k equal to j, so one part may span no lane.
-->

---

# Backup: derived operators and conventions

<div class="grid gap-6" style="grid-template-columns: 1fr 1fr">
<div class="formulas">

Somewhere: $\langle\varphi\rangle \equiv \begin{array}{c}\mathit{true}\\ \mathit{true}\frown\varphi\frown\mathit{true}\\ \mathit{true}\end{array}$

$\mathit{free} \equiv \neg\exists c \in I\colon \langle \mathit{re}(c) \lor \mathit{cl}(c)\rangle$

$\mathit{safe} \equiv \neg\exists c \in I\colon (c \neq E \land \langle \mathit{re}(c) \land \mathit{re}(E)\rangle)$

$\mathit{pc}(\mathit{ego}) \equiv \exists c \in I\colon c \neq \mathit{ego} \land \langle \mathit{cl}(\mathit{ego}) \land (\mathit{re}(c) \lor \mathit{cl}(c))\rangle$

</div>
<div>
<ul class="small">
  <li>Virtual view <Tex e="V(E) = (L, X)" /> with <Tex e="X = [\mathit{pos}(E) - h, \mathit{pos}(E) + h]" />. The horizon <Tex e="h" /> exceeds every safety envelope.</li>
  <li>The quantifier ranges over <Tex e="I_{V(E)}" />: the cars whose reservation or claim overlaps <Tex e="V(E)" />. A car outside the view reserves and claims nothing in it.</li>
  <li>The vertical chop admits <Tex e="k = i - 1" /> and <Tex e="k = j" />: one part may span no lane. So <Tex e="\langle\varphi\rangle" /> also works on the top and bottom lanes.</li>
  <li>Two spaces that share only the chopping point do not overlap. So <Tex e="\mathit{re}(C) \frown \mathit{free}" /> is satisfiable.</li>
</ul>
</div>
</div>

<style>
.formulas p { margin: 0 0 14px 0; }
</style>

<!--
Backup. The derived operators and the conventions that evaluation inside a bounded view forces.

Somewhere, free, safe, and the potential collision pc of the controllers.

The quantifier ranges over the cars in the view, not over all cars. The vertical chop admits empty lane sets on one side, so somewhere works on the outermost lanes. And two spaces that meet in one point do not overlap, so a reservation that ends where a free space begins leaves that space free.
-->

---

# Backup: transitions of a traffic snapshot

<p class="muted small" style="margin-top:-6px">A traffic snapshot <Tex e="TS" /> gives, for each car, its position, speed and acceleration, and the segments that it claims or reserves.</p>

<div class="grid gap-6" style="grid-template-columns: 1fr 1.7fr; margin-top: 8px">
<div>
  <div class="box box-grey small">
    <b>Time transitions</b> <Tex e="TS \xrightarrow{t} TS'" /><br>
    Time passes. Every car advances according to its speed and acceleration.
  </div>
  <div class="box box-grey small mt-3">
    <b>Action transitions</b> <Tex e="TS \xrightarrow{\alpha} TS'" /><br>
    Labelled with an action <Tex e="\alpha" /> of one car <Tex e="C" />.
  </div>
  <p class="tiny muted mt-3">Only actions that involve a choice carry a parameter. <Tex e="r(C)" /> needs none: a car may reserve only space that it already claims. Full definitions: Schwammberger (2018).</p>
</div>
<div>
<table class="kit-table trans">
  <tbody>
    <tr><td><Tex e="\mathit{acc}(C, n)" /></td><td><Tex e="C" /> sets its acceleration to <Tex e="n" />.</td></tr>
    <tr><td><Tex e="c(C, n)" /></td><td><Tex e="C" /> claims the adjacent lane segment <Tex e="n" />: it announces a lane change.</td></tr>
    <tr><td><Tex e="\mathit{cc}(C)" /></td><td><Tex e="C" /> claims its path through the next crossing.</td></tr>
    <tr><td><Tex e="\mathit{wd}\ c(C)" />, <Tex e="\mathit{wd}\ \mathit{cc}(C)" /></td><td><Tex e="C" /> withdraws that claim and abandons the manoeuvre, e.g. because another car claims or reserves the same space.</td></tr>
    <tr><td><Tex e="r(C)" />, <Tex e="\mathit{rc}(C)" /></td><td><Tex e="C" /> turns its claim into a reservation and starts the manoeuvre.</td></tr>
    <tr><td><Tex e="\mathit{wd}\ r(C, n)" /></td><td><Tex e="C" /> completes the lane change. It keeps only segment <Tex e="n" /> reserved.</td></tr>
    <tr><td><Tex e="\mathit{wd}\ \mathit{rc}(C)" /></td><td><Tex e="C" /> completes the crossing and releases the crossing segments.</td></tr>
  </tbody>
</table>
</div>
</div>

<style>
.trans { font-size: 13px; }
.trans td, .trans td:first-child { text-align: left; vertical-align: top; }
.trans td:first-child { white-space: nowrap; }
</style>

<!--
Backup. How traffic moves between snapshots, as in Section 3 of the paper.

Time transitions let time pass. Every car advances according to its speed and acceleration.

Action transitions are labelled with controller actions of one car: accelerate, claim and claim-crossing, withdraw a claim, reserve and reserve-crossing, and withdraw a reservation when the manoeuvre is complete.

In UMLSL-Sim, one frame is one time transition, after every car has performed its actions. The simulator performs cc and wd cc itself, through the crossing-claim lease.
-->
