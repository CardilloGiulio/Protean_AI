# Canon research notes for built-in timeline phases

These sources are research references used to constrain the built-in phase data. Protean does **not** fetch them at runtime; character cards remain local declarative data.

## Persona 5 Royal

- Official Persona 5 Royal — Ann Takamaki character page: https://p5r.jp/character/anne/
- Official Persona 5 Royal character overview (Ann, Makoto and others): https://p5r.jp/gad4.html
- Makoto Niijima overview / story progression: https://en.wikipedia.org/wiki/Makoto_Niijima
- Ann Takamaki overview / Kamoshida background: https://en.wikipedia.org/wiki/Ann_Takamaki
- Megami Tensei Wiki character references were used as secondary cross-checks for personality/arc distinctions.

## Harry Potter

- Wizarding World — Hermione's early first-year friendship/troll turning point: https://www.harrypotter.com/features/what-if-quirrell-had-never-let-a-troll-loose-in-the-dungeon
- Wizarding World — Hermione's changing willingness to break rules for friends: https://www.harrypotter.com/features/why-harry-and-hermione-had-the-best-platonic-friendship
- Hermione Granger overview: https://en.wikipedia.org/wiki/Hermione_Granger
- Harry Potter Wiki — 1942–1943 Chamber opening and sixteen-year-old Tom Riddle: https://harrypotter.fandom.com/wiki/Chamber_of_Secrets
- Harry Potter Wiki — T. M. Riddle's Diary: https://harrypotter.fandom.com/wiki/T._M._Riddle%27s_Diary

## Neon Genesis Evangelion

- Evangelion timeline reference: https://evangelion.fandom.com/wiki/Timeline
- Misato Katsuragi character reference: https://evangelion.fandom.com/wiki/Misato_Katsuragi

## Design rule

Sources establish chronology; they do not become runtime RAG context. The system prompt receives only the locally reviewed character phase data. This keeps web retrieval outside the character/runtime security and prompt boundaries.


## 0.5.0 roster/content expansion references

These public sources were used to cross-check central roster identities and broad canon chronology while writing the new built-in cards. Character.AI-style public roleplay listings were used only as design inspiration for *event-hook scene framing* (caught-in-the-act, mission complication, aftermath); Protean does not copy third-party character scripts or greetings.

- Persona 5 Royal official character material: https://p5r.jp/ and https://persona.atlus.com/p5r/
- Evangelion official character material: https://www.evangelion.jp/1_0/chara.html and https://www.evangelion.jp/news/eva25th1004/
- Demon Slayer official character material: https://demonslayer-anime.com/hta/character/ and https://demonslayer-anime.com/mugentrainarc/character/
- Hunter x Hunter / VIZ overview and Hunter Exam material: https://www.viz.com/hunter-x-hunter and https://www.viz.com/blog/posts/welcome-to-hunter-x-hunter
- Harry Potter / Wizarding World canon material: https://www.harrypotter.com/

The cards remain intentionally phase-gated. If a detail is not established by the selected phase, later-canon knowledge must remain unavailable even if a scenario references an unusual place or event.
