# Mission 3 — Let People Plug In Their Own AI Photo Model — In Plain English

_For Roger. No jargon, no code references. One screen._

> **Status: CHARTERED, NOT YET BUILT.** This is the plan for the next mission. Nothing has been built
> yet. When it is, you will verify it by hand with `docs/manual testing/MISSION_3_MANUAL_TESTING.md`.
> Until then, every test case in that document is expected to **fail** — it describes the gap this
> mission closes, and doubles as the acceptance checklist you tick off at the end.

## What is this mission?

The program can look at listing photos and note things about them — bright rooms, stainless
appliances, and so on. Today that "looking" is done by a simple hand-written rule of thumb, not by a
real AI model. But the plumbing to accept a **real** AI model already exists inside the program — it
was built and tested a while ago. The catch: there is no way for anyone to actually switch it on.
There is no button, no setting, nothing. This mission adds that switch, so someone can point the
program at their own trained AI photo model and have it used for real.

## Why are we doing it / what problem does it solve?

Right now the program advertises that it has an "AI photo" capability, and internally it even has a
proper slot ready to hold a real model — but that slot is impossible to fill from the outside. It is
like a car with a fully wired trailer hitch that has been welded shut: the hard part is done, yet no
one can use it. That is a small, cheap gap to close, and closing it is the single highest
value-for-effort step toward the program having a genuine AI capability rather than a stand-in.

It also quietly unlocks something else. There are six things the program currently can only **guess** at
from a photo's file name (like a file called `mold_basement.jpg`), and today it is honest enough to
treat those as unconfirmed hints that never affect the money. The moment a real photo model that
actually recognizes those things is plugged in, those six guesses can graduate to **confirmed
observations** — and that happens automatically, with no extra work, the day someone brings a model
that covers them.

## What are the goals?

- Add a real way — a command-line switch and matching settings — to plug in your own trained photo AI
  model.
- Make the program actually **use** that model once it is plugged in (today it would ignore it).
- Make the report honestly show that a real model produced the observations, clearly distinct from the
  built-in stand-in.
- Let those six "guess-only" photo labels become confirmed findings when a model that recognizes them
  is supplied — with no change to the program's list of things it understands.
- Ship it safely: a security check on loading someone's model file, and honest wording that never
  overclaims.

## What will we have when it's done that we don't now?

- **Before:** the "bring your own AI model" ability exists but is completely unreachable — no switch
  can turn it on. **After:** you point the program at your model file and its labels, and it uses it.
- **Before:** the report can only ever say the photo observations came from the built-in stand-in.
  **After:** when you supply a real model, the report says so — clearly, and without pretending the
  program vouches for how accurate *your* model is.
- **Before:** those six file-name guesses can never be confirmed by anything. **After:** a suitable
  model confirms them, and only then do they count as real observations.
- **Before:** giving the program a broken or missing model file could produce an ugly crash.
  **After:** you get a clean, plain message telling you what went wrong.

## What it deliberately will NOT do (left open on purpose)

- It will **not** add the "paste in your API key to a hosted AI service" option — that is a separate,
  bigger piece with cost and privacy questions of its own.
- It will **not** ship a ready-made real-estate photo AI model with the program — that is the largest
  piece (training, licensing, and standing behind its accuracy) and is not part of this.
- It will **not** touch the financial engine, change any pass/fail verdict, or teach the program any
  new photo concepts. The AI only *observes*; the money math and the buy/decline decision stay exactly
  as they are.

## How you'll know it worked

Follow `docs/manual testing/MISSION_3_MANUAL_TESTING.md`. It walks you through setting up a tiny test
model, plugging it in, and watching the program actually use it — the report showing a real model was
used, the six labels becoming confirmed, and the error messages staying clean when you feed it a bad
file. Every step has a clear yes/no so nothing can pretend to be finished when it isn't.
