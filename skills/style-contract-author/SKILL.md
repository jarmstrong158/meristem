---
name: style-contract-author
description: Help the user define or adjust a Meristem style contract (locked palette, canvas sizes, outline/shading rules) so all assets read as one game. Use when someone wants a specific visual style.
---

# Style-contract author

The style contract is what makes independently-generated assets read as **one artist's game** (proven
in the Phase 0 bake-off). Your job is to help the user pin it down without turning it into a chore.

## Defaults first
Every scaffolded project starts with the **PICO-8 (CC0)** 16-color palette and sane canvas/outline/
shading/anchor rules. Most users should keep these. Only change what they actually care about.

## When the user wants a different look
- **Palette.** If they want a different palette, keep it to **16 CC0 / clearly-licensed colors** and
  record the source + license in the contract. Warn them off palettes with no license (Endesga-32,
  Sweetie-16 have no formal grant — usable but flag it). Never exceed the locked count.
- **Canvas sizes.** Per asset class (tile 16, character 32…). Keep them multiples of the grid base unit.
- **Outline / shading / anchor.** Selective dark outline, N ramp steps, light direction, pivot per class.

## How to write it
Edit the `style_contract` domain via the spec-store: `get_domain("style_contract")`, change the value,
`diff_domain` to preview, `set_domain` to commit (it's schema-validated — rejected if malformed).

## Sanity check
After a change, remind the user they can regenerate assets and eyeball a contact sheet — the contract
is only "right" when the set looks coherent at 1×, not when the JSON is valid. Palette adherence and
hard alpha are enforced by the asset gate automatically; coherence is the human call.
