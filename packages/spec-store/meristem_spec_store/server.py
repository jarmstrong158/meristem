"""MCP server for the spec store.

Exposes read tools, a single validated write (per-domain, schema-enforced — there is
NO raw write-anything tool), a diff tool, and validate_all. State persists to a
manifest JSON file (env MERISTEM_MANIFEST, default ./meristem.manifest.json).

The tool handlers are plain functions on `SpecService` so they can be unit-tested
without an MCP runtime; `build_server()` wires them into FastMCP.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .schemas import DOMAINS
from .store import SpecStore, SpecValidationError


class SpecService:
    """Transport-agnostic handlers. One instance backs the MCP server."""

    def __init__(self, manifest_path: str | Path):
        self.path = Path(manifest_path)
        self.store = SpecStore.load(self.path) if self.path.exists() else SpecStore()

    def _persist(self) -> None:
        self.store.save(self.path)

    # ---- reads ----
    def list_domains(self) -> dict:
        return {"known": DOMAINS, "present": sorted(self.store.domains)}

    def get_domain(self, domain: str) -> dict:
        if domain not in DOMAINS:
            return {"error": f"unknown domain {domain!r}", "known": DOMAINS}
        return {"domain": domain, "value": self.store.get(domain)}

    def get_manifest(self) -> dict:
        return {"version": self.store.version, "domains": self.store.get_all()}

    # ---- the only mutation: validated, per-domain ----
    def set_domain(self, domain: str, value: dict, actor: str = "agent", reason: str = "") -> dict:
        try:
            self.store.set_domain(domain, value, {"actor": actor, "reason": reason})
        except SpecValidationError as e:
            return {"accepted": False, "domain": e.domain, "errors": e.errors}
        except KeyError as e:
            return {"accepted": False, "errors": [str(e)]}
        self._persist()
        return {"accepted": True, "domain": domain, "version": self.store.version}

    # ---- scaffold a strawman (game-interview on-ramp) ----
    def scaffold_project(self, title: str = "Untitled", genre: str = "adventure",
                         control: str = "top_down_controller",
                         premise: str = "A hero sets out on a journey.",
                         protagonist: str = "Hero", enemy: str = "Slime",
                         biome: str = "grass") -> dict:
        from .scaffold import strawman
        try:
            domains = strawman(title=title, genre=genre, control=control, premise=premise,
                               protagonist=protagonist, enemy=enemy, biome=biome)
        except ValueError as e:
            return {"accepted": False, "errors": [str(e)]}
        for domain, value in domains.items():
            self.store.set_domain(domain, value, {"actor": "scaffold"})
        self._persist()
        report = self.store.validate_all()
        return {"accepted": report.ok, "version": self.store.version,
                "domains": sorted(domains), "validation": report.to_dict()}

    # ---- discover the sprite vocabulary (what entities/items can pick) ----
    def list_sprite_archetypes(self) -> dict:
        try:
            from meristem_generators import sprite_catalog
        except ImportError as e:  # a declared dependency: this means a broken install
            return {"available": False, "reason": str(e), "archetypes": [],
                    "warning": "meristem_generators is not importable, so the sprite "
                               "vocabulary is UNKNOWN — this is not an empty catalog"}
        return {"available": True, "archetypes": sprite_catalog()}

    def check_sprite(self, archetype: str, config: dict | None = None) -> dict:
        """Validate a single sprite descriptor before writing it — same check the
        cross-ref runs, but for one pick, so the author gets immediate feedback.

        `problems` are errors (an unknown archetype, or a variant value that is not a
        real build). `warnings` are config KEYS the archetype does not read: those
        cannot fail a build, but they silently do nothing, which is worse to debug."""
        try:
            from meristem_generators import sprite_warnings, validate_sprite
        except ImportError as e:
            # NOT ok: the check did not run. Reporting ok=True here would be the same
            # bug as a validation report that greens a check it skipped.
            return {"available": False, "reason": str(e), "ok": False, "problems": [],
                    "warnings": [], "checks_skipped": [f"sprite_archetypes: {e}"]}
        problems = validate_sprite(archetype, config or {})
        return {"available": True, "ok": not problems, "problems": problems,
                "warnings": sprite_warnings(archetype, config or {}),
                "checks_skipped": []}

    # ---- render, so the author can actually LOOK at the pick ----
    def _contract(self):
        """(contract, None) or (None, reason).

        The style contract is read from the MANIFEST — the compiler builds assets from
        `domains["style_contract"]`, so a preview must render against that same
        contract or it is previewing a different game than the one that will compile.
        No env var, no invented default path."""
        raw = self.store.get("style_contract")
        if not raw:
            return None, ("the manifest has no style_contract domain yet, so there is no "
                          "canvas or palette to render against — run scaffold_project, "
                          "or set the style_contract domain first")
        try:
            from asset_gate.contract import StyleContract
        except ImportError as e:                     # a declared dependency: broken install
            return None, (f"asset_gate is not importable ({e}), so the style contract "
                          "cannot be loaded and nothing can be rendered")
        try:
            return StyleContract.from_dict(raw), None
        except Exception as e:
            return None, f"the manifest's style_contract could not be loaded: {e}"

    def _render(self, fn, archetype: str, config: dict | None, **kw) -> dict:
        contract, reason = self._contract()
        if contract is None:
            return {"ok": False, "reason": reason}
        try:
            import meristem_generators as gen
        except ImportError as e:
            return {"ok": False, "reason": f"meristem_generators is not importable ({e})"}
        # Refuse to render an invalid descriptor rather than show the fallback. A
        # typo'd build renders the archetype's DEFAULT, so previewing it would put a
        # picture of a dog under the label "dragon" and read as confirmation.
        problems = gen.validate_sprite(archetype, config or {})
        if problems:
            return {"ok": False, "reason": "invalid sprite descriptor", "problems": problems}
        try:
            png, meta = getattr(gen, fn)(contract, archetype, config, **kw)
        except (KeyError, ValueError) as e:
            return {"ok": False, "reason": str(e)}
        out = {"ok": True, "png": png, "warnings": gen.sprite_warnings(archetype, config or {}),
               **meta}
        try:                                          # conformance, alongside the picture
            from asset_gate import validate
            res = validate(gen.build_archetype(contract, archetype, config or {}),
                           gen.archetype_class(archetype), contract)
            out["gate"] = {"accepted": res.accepted, "reasons": res.reasons}
        except ImportError:
            out["gate"] = {"accepted": None, "reasons": ["asset_gate not importable"]}
        return out

    def preview_sprite(self, archetype: str, config: dict | None = None, scale: int = 6,
                       frame: int = 0, silhouette: bool = False) -> dict:
        return self._render("render_sprite", archetype, config, scale=scale, frame=frame,
                            silhouette=silhouette)

    def compare_builds(self, archetype: str, config: dict | None = None, scale: int = 5,
                       silhouette: bool = True) -> dict:
        return self._render("render_builds", archetype, config, scale=scale,
                            silhouette=silhouette)

    # ---- diff + whole-manifest validation ----
    def diff_domain(self, domain: str, candidate: dict) -> dict:
        return self.store.diff_domain(domain, candidate)

    def validate_all(self) -> dict:
        return self.store.validate_all().to_dict()


def default_manifest_path() -> Path:
    return Path(os.environ.get("MERISTEM_MANIFEST", "meristem.manifest.json"))


# ---- MCP Apps (SEP-1865, Final) spec-inspector panel ----
SPEC_INSPECTOR_URI = "ui://meristem/spec-inspector.html"
SPEC_INSPECTOR_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{font:13px system-ui,sans-serif;margin:0;padding:12px;background:#1a1b26;color:#c0caf5}
h2{margin:0 0 8px;font-size:15px}.ok{color:#9ece6a}.bad{color:#f7768e}.warn{color:#e0af68}
.dom{display:flex;justify-content:space-between;padding:4px 8px;border-radius:6px;background:#24283b;margin:3px 0}
.miss{opacity:.4}.err{color:#f7768e;font-size:12px;margin:2px 0 2px 8px}
button{background:#7aa2f7;border:0;color:#1a1b26;padding:6px 10px;border-radius:6px;cursor:pointer;font-weight:600}
</style></head><body>
<h2>Meristem manifest <span id="ver"></span></h2>
<div id="status"></div><div id="domains"></div><div id="errors"></div>
<p><button id="reval">Re-validate</button></p>
<script>
let _id=0;
function rpc(m,p){window.parent.postMessage({jsonrpc:"2.0",id:++_id,method:m,params:p},"*");}
function render(sc){
  if(!sc)return;
  document.getElementById("ver").textContent=sc.version!=null?("v"+sc.version):"";
  var v=sc.validation||{};
  var sk=v.checks_skipped||[];
  var head=v.ok
    ?'<div class="ok">&#10003; valid &mdash; schemas + cross-references</div>'
    :'<div class="bad">&#10007; invalid</div>';
  // a skipped check must never read as a passed check
  if(sk.length){head+='<div class="warn">&#9888; '+sk.length+' check(s) SKIPPED &mdash; not verified:</div>'
    +sk.map(function(s){return '<div class="warn err">&bull; '+s+'</div>';}).join("");}
  document.getElementById("status").innerHTML=head;
  var doms=sc.domains||{};
  document.getElementById("domains").innerHTML=Object.keys(doms).map(function(d){
    return '<div class="dom '+(doms[d]?'':'miss')+'"><span>'+d+'</span><span>'+(doms[d]?'\\u25CF':'\\u2014')+'</span></div>';}).join("");
  var errs=[];var se=v.schema_errors||{};
  (v.missing_domains||[]).forEach(function(d){errs.push("missing required domain: "+d);});
  for(var k in se){(se[k]||[]).forEach(function(e){errs.push(k+": "+e);});}
  (v.crossref_errors||[]).forEach(function(e){errs.push("cross-ref: "+e);});
  document.getElementById("errors").innerHTML=errs.map(function(e){return '<div class="err">&bull; '+e+'</div>';}).join("");
}
window.addEventListener("message",function(e){
  var m=e.data||{};
  if(m.method==="ui/notifications/tool-result"){render(m.params&&m.params.structuredContent);}
});
document.getElementById("reval").onclick=function(){rpc("tools/call",{name:"inspect_manifest",arguments:{}});};
rpc("ui/initialize",{appInfo:{name:"meristem-spec-inspector"},capabilities:{}});
</script></body></html>"""


def _inspector_payload(store: SpecStore) -> dict:
    return {"version": store.version,
            "domains": {d: (store.domains.get(d) is not None) for d in DOMAINS},
            "present": sorted(store.domains),
            "validation": store.validate_all().to_dict()}


def build_server(service: Optional[SpecService] = None):
    # imported lazily so the library still works without the optional `mcp` extra
    from mcp.server.fastmcp import FastMCP, Image

    svc = service or SpecService(default_manifest_path())
    mcp = FastMCP("meristem-spec-store")

    @mcp.tool(description="List known and currently-present manifest domains.")
    def list_domains() -> dict:
        return svc.list_domains()

    @mcp.tool(description="Read one manifest domain's current value.")
    def get_domain(domain: str) -> dict:
        return svc.get_domain(domain)

    @mcp.tool(description="Read the whole manifest (all domains + version).")
    def get_manifest() -> dict:
        return svc.get_manifest()

    @mcp.tool(description="Set a whole domain. Rejected (not coerced) if it fails that domain's schema. "
                          "This is the only write; there is no raw write-anything tool.")
    def set_domain(domain: str, value: dict, actor: str = "agent", reason: str = "") -> dict:
        return svc.set_domain(domain, value, actor, reason)

    @mcp.tool(description="Scaffold a complete, valid strawman manifest from high-level answers "
                          "(the game-interview on-ramp). Fills all 10 domains — including a real "
                          "starter level and two starter abilities; the model then enriches.")
    def scaffold_project(title: str = "Untitled", genre: str = "adventure",
                         control: str = "top_down_controller",
                         premise: str = "A hero sets out on a journey.",
                         protagonist: str = "Hero", enemy: str = "Slime", biome: str = "grass") -> dict:
        return svc.scaffold_project(title, genre, control, premise, protagonist, enemy, biome)

    @mcp.tool(description="List the sprite vocabulary an entity/item can pick: every archetype with "
                          "its class, whether it animates, its build/kind/shape options, and colour knobs. "
                          "For humanoids this includes prop/accessory layers (held item, garment, feet, "
                          "arms, hair_accent) — the way to make characters distinct by SILHOUETTE, not "
                          "just palette. Call this before setting an entity/item sprite so you choose real options.")
    def list_sprite_archetypes() -> dict:
        return svc.list_sprite_archetypes()

    @mcp.tool(description="Validate one sprite descriptor {archetype, config} before writing it: checks "
                          "the archetype exists and each build/kind/shape is a known option. Returns "
                          "{ok, problems, warnings} — `problems` are errors, `warnings` are config KEYS "
                          "this archetype does not read (a typo like 'shpae' or 'hat_colour' cannot fail "
                          "a build, it just silently does nothing). Use after list_sprite_archetypes.")
    def check_sprite(archetype: str, config: dict = None) -> dict:
        return svc.check_sprite(archetype, config)

    def _image_result(res: dict):
        """A render result as [image, metadata], so the caller SEES the sprite and also
        gets the structured facts. On failure there is no image — just the reason."""
        if not res.get("ok"):
            return res
        png = res.pop("png")
        return [Image(data=png, format="png"), res]

    @mcp.tool(description="RENDER one sprite to a PNG you can look at, from {archetype, config}. "
                          "The asset gate only checks conformance (canvas, hard alpha, palette) — it "
                          "cannot tell you whether a sprite reads as the thing it is named, so LOOK at "
                          "the result before writing the descriptor. `scale` magnifies with "
                          "nearest-neighbour (default 6); `frame` picks an animation frame (0 is always "
                          "the static build); `silhouette` renders the alpha mask alone, which is how "
                          "you check the shape reads before any interior detail. Renders against the "
                          "manifest's own style_contract, and refuses a descriptor that would silently "
                          "fall back to the default build.")
    def preview_sprite(archetype: str, config: dict = None, scale: int = 6,
                       frame: int = 0, silhouette: bool = False):
        return _image_result(svc.preview_sprite(archetype, config, scale, frame, silhouette))

    @mcp.tool(description="RENDER every variant of one archetype side by side, labelled, as a "
                          "distinctness review. Defaults to SILHOUETTES because that is the question "
                          "this answers: variants that share an outline read as the same thing on "
                          "screen no matter how different their interior detail or palette is. Pass "
                          "silhouette=false to compare the finished art instead. Use this whenever you "
                          "add or change a build.")
    def compare_builds(archetype: str, config: dict = None, scale: int = 5,
                       silhouette: bool = True):
        return _image_result(svc.compare_builds(archetype, config, scale, silhouette))

    @mcp.tool(description="Diff a candidate value for a domain against the stored value.")
    def diff_domain(domain: str, candidate: dict) -> dict:
        return svc.diff_domain(domain, candidate)

    @mcp.tool(description="Validate the whole manifest: per-domain schemas + cross-references + "
                          "required-domain completeness. Returns {ok, complete, schema_errors, "
                          "crossref_errors, missing_domains, checks_skipped, summary}. `ok` means "
                          "no errors were FOUND; `complete` also means every check actually RAN — "
                          "always read checks_skipped before treating a report as green.")
    def validate_all() -> dict:
        return svc.validate_all()

    # ---- MCP Apps (SEP-1865) spec-inspector panel + its tool ----
    @mcp.resource(SPEC_INSPECTOR_URI, mime_type="text/html;profile=mcp-app",
                  meta={"ui": {"csp": {"resourceDomains": []}}})
    def spec_inspector_view() -> str:
        return SPEC_INSPECTOR_HTML

    @mcp.tool(
        description="Show the manifest in an inline inspector panel (domains + validation). "
                    "Returns the same data as structured content, so hosts without MCP-Apps still get it.",
        meta={"ui": {"resourceUri": SPEC_INSPECTOR_URI}, "ui/resourceUri": SPEC_INSPECTOR_URI},
    )
    def inspect_manifest() -> dict:
        return _inspector_payload(svc.store)

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
