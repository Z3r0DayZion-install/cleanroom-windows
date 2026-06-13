# Cleanroom PR #21 — Manual Gate + App Title Polish

## Goal

Finish the real-session validation for Cleanroom PR #21 and make the app title/header feel like a real product, not a placeholder dev label.

Cleanroom is starting to feel like a real Windows utility. Do not bury that under a plain/default title treatment.

---

## Branch / Scope

Current pressure point:

```text
PR #21: feat/shell-context-menus
```

Primary goal:

```text
Manual real Windows-session proof for Explorer shell menus + row context actions.
```

Secondary UI polish:

```text
Make the in-app “Cleanroom” title/header feel special and branded.
```

Do not add unrelated features. Do not rewrite the app. Do not touch release/version/tagging unless explicitly approved.

---

## Part 1 — Manual Real-Session Gate

Automated tests are not enough for this PR. This needs real Windows-session proof.

Run and document the following:

### Explorer Shell Menu

- [ ] Install Explorer shell menu
- [ ] Confirm it appears in Windows Explorer where expected
- [ ] Remove Explorer shell menu
- [ ] Confirm it disappears cleanly
- [ ] Confirm no HKLM/admin prompt unless explicitly required
- [ ] Confirm no broken registry leftovers

### Archive / Restore / Receipt Rows

Right-click real archive/receipt rows and verify:

- [ ] Archive
- [ ] Restore
- [ ] Open receipt
- [ ] Copy archive path
- [ ] Copy receipt path
- [ ] Delete confirmation
- [ ] Cancel delete path
- [ ] Confirm delete only happens after confirmation

### Layout

Confirm UI still holds:

- [ ] 1080px shell width
- [ ] Toolbar remains on its own row
- [ ] Row context menus do not overlap/cut off
- [ ] No weird overflow
- [ ] No broken spacing

### Automated Preflight (repo)

Before manual session work, run from repo root:

```powershell
python -m pytest
python scripts/shell_context_menu_manual_gate.py
python scripts/ui_merge_gates.py --include-150
python scripts/verify_release_surface.py --tag v1.0.4
```

### Required Output

Report PASS/FAIL per item.

Include screenshots for anything visual or questionable.

**Do not merge PR #21 until the manual gate passes.**

---

## Part 2 — Make the Cleanroom Title Special

The current app title/header should feel more like a finished product.

Do a focused visual polish pass on the **Cleanroom title area only**.

### Direction

The title should communicate:

```text
Cleanroom
Archive-first cleanup
Proof-backed
Reversible
Calm Windows utility
```

It should not feel like a generic `<h1>`.

### Preferred Title Concept

Create a branded title lockup:

```text
Cleanroom
Archive-first cleanup, with receipts.
```

Or shorter:

```text
Cleanroom
Archive-first Windows cleanup.
```

**Strongest title choice:**

```text
Cleanroom
Archive-first cleanup, with receipts.
```

That says exactly what makes it different without sounding fake.

### Visual Treatment

Make the app title feel premium but still practical:

- “Cleanroom” should be the dominant wordmark
- Use a subtle glow, cut-line, receipt/check motif, or archive-safe badge
- Add a small proof/custody accent if it fits
- Keep it clean, not flashy
- No fake score
- No fake claims
- No clutter

Possible micro-elements:

- Small receipt/check icon beside the title
- Subtle “Receipt-backed” pill
- Small “Archive-first” subtitle
- Thin divider line that feels like a custody/proof trail
- Soft blue/green accent glow, but restrained

### Avoid

Do not make it look like:

- A gamer app
- Antivirus scareware
- Crypto dashboard
- Fake “AI cleaner”
- Loud neon SaaS landing page
- Childish mascot branding

Cleanroom should feel like a serious Windows utility with proof.

### Suggested Pill

If space allows:

```text
Proof-backed
```

or

```text
Receipt-backed
```

---

## Acceptance Criteria For Title Polish

Pass only if:

- [ ] “Cleanroom” feels intentionally branded
- [ ] Subtitle explains the product in one glance
- [ ] Title area still fits the existing app layout
- [ ] No layout regression at normal window size
- [ ] No cramped header
- [ ] No excessive glow
- [ ] No new fake claims
- [ ] Screenshots prove the before/after

---

## Verification Required

Before reporting done:

- [ ] App launches cleanly
- [ ] Manual shell-menu checklist completed
- [ ] Right-click row actions verified
- [ ] Title/header screenshot captured
- [ ] Layout screenshot at 1080px captured
- [ ] Tests still pass
- [ ] Build still passes

Report:

```text
Changed files:
Verification:
Manual gate result:
Screenshots:
Merge recommendation:
```

---

## Hard Rules

- Do not merge until manual Windows-session proof passes.
- Do not tag.
- Do not release.
- Do not start a larger redesign.
- Do not add new product claims unless the app proves them.
