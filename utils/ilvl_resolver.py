"""
Post-midnight ilvl resolver.

Computes item level from item_id, bonus_lists, and optional drop_level using
Raidbots bonuses.json, equippable-items.json, item-curves.json, and item-squish-era.json.
See plan §4.3 for pseudo-code.
"""


def _get_base_item_level(item_id, equippable_items):
    """Get DBC base item level from equippable-items. Returns None if missing."""
    if not equippable_items:
        return None
    keys = [str(item_id)]
    try:
        keys.append(int(item_id))
    except (TypeError, ValueError):
        pass
    for key in keys:
        if key not in equippable_items:
            continue
        entry = equippable_items[key]
        if isinstance(entry, dict):
            v = entry.get("baseItemLevel") or entry.get("base_level") or entry.get("ilvl")
            if v is not None:
                return v
    return None


def _apply_curve(value, curve_id, item_curves):
    """Apply curve from item-curves.json to value. Returns value unchanged if missing."""
    if not item_curves or curve_id is None:
        return value
    c = item_curves.get(str(curve_id)) if isinstance(item_curves, dict) else None
    if not c:
        return value
    # Curve format TBD; may be points, formula, or lookup. Stub: pass through.
    points = c.get("points") or c.get("curve") or []
    if isinstance(points, list) and len(points) >= 2:
        # Simple linear interpolation between first and last point if value in range
        try:
            xs = [p[0] if isinstance(p, (list, tuple)) else p.get("x", p) for p in points]
            ys = [p[1] if isinstance(p, (list, tuple)) else p.get("y", p) for p in points]
            if xs and ys and min(xs) <= value <= max(xs):
                # Nearest or interpolate; keep simple
                for i, x in enumerate(xs):
                    if value <= x:
                        if i == 0:
                            return ys[0]
                        t = (value - xs[i - 1]) / (x - xs[i - 1]) if x != xs[i - 1] else 1
                        return int(ys[i - 1] + t * (ys[i] - ys[i - 1]))
                return ys[-1]
        except (TypeError, IndexError, ZeroDivisionError):
            pass
    return value


def resolve_post_midnight_ilvl(
    item_id,
    bonus_lists,
    drop_level,
    bonuses_by_id,
    equippable_items,
    item_curves,
    item_squish_era,
):
    """
    Compute post-midnight item level from bonus_lists and optional drop_level.

    Returns int item level, or None if base level missing or unresolvable.
    """
    base = _get_base_item_level(item_id, equippable_items)
    if base is None:
        return None

    item_level = int(base)
    legacy_level_offset = 0
    set_level_ops = {}  # era -> [(priority, amount), ...]
    level_offset_ops = {}  # era -> [amount, ...]
    level_offset_secondary = []
    drop_level_ops = {}  # era -> [(priority, curve_id, offset), ...]

    for bid in bonus_lists or []:
        b = bonuses_by_id.get(int(bid)) if bonuses_by_id else None
        if not b or not isinstance(b, dict):
            continue

        il = b.get("itemLevel")
        if il is not None:
            era = il.get("squishEra", 0) if isinstance(il, dict) else 0
            pr = il.get("priority", 9999) if isinstance(il, dict) else 9999
            amt = il.get("amount") if isinstance(il, dict) else il
            if amt is not None:
                set_level_ops.setdefault(era, []).append((pr, amt))

        lo = b.get("levelOffset")
        if lo is not None:
            era = lo.get("squishEra", 0) if isinstance(lo, dict) else 0
            amt = lo.get("amount") if isinstance(lo, dict) else lo
            if amt is not None:
                level_offset_ops.setdefault(era, []).append(amt)

        los = b.get("levelOffsetSecondary")
        if los is not None:
            amt = los.get("amount") if isinstance(los, dict) else los
            if amt is not None:
                level_offset_secondary.append(amt)

        dlc = b.get("dropLevelCurve")
        if dlc is not None and isinstance(dlc, dict):
            era = dlc.get("squishEra", 0)
            cid = dlc.get("curveId")
            off = dlc.get("offset", 0)
            pr = dlc.get("priority", 9999)
            drop_level_ops.setdefault(era, []).append((pr, cid, off))

        leg = b.get("level")
        if leg is not None and isinstance(leg, (int, float)):
            legacy_level_offset += int(leg)

    has_ops = (
        bool(set_level_ops)
        or bool(level_offset_ops)
        or bool(level_offset_secondary)
        or bool(drop_level_ops)
    )

    if not has_ops:
        return item_level + legacy_level_offset

    eras = item_squish_era if isinstance(item_squish_era, list) else []
    if not eras and isinstance(item_squish_era, dict):
        eras = item_squish_era.get("eras", item_squish_era.get("data", []))

    if not eras:
        return item_level + legacy_level_offset

    for era_def in eras:
        curve_id = None
        if isinstance(era_def, dict):
            curve_id = era_def.get("curveId") or era_def.get("curve_id")
        if curve_id is not None:
            item_level = _apply_curve(item_level, curve_id, item_curves)

        era_id = era_def.get("id", era_def.get("eraId", 0)) if isinstance(era_def, dict) else 0

        sl = set_level_ops.get(era_id) or set_level_ops.get(0)
        if sl:
            best = min(sl, key=lambda x: x[0])
            item_level = int(best[1])

        dl = drop_level_ops.get(era_id) or drop_level_ops.get(0)
        if dl and drop_level is not None:
            best = min(dl, key=lambda x: x[0])
            _, cid, off = best
            lookup = drop_level if cid else 0
            scaled = _apply_curve(lookup, cid, item_curves) if cid else lookup
            item_level = int(scaled) + int(off)

        los_era = level_offset_ops.get(era_id) or level_offset_ops.get(0)
        if los_era:
            for amt in los_era:
                item_level += int(amt)

    for amt in level_offset_secondary:
        item_level += int(amt)

    return item_level
