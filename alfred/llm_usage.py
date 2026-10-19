#!/usr/bin/env python3 -S

"""
Show LLM usage limits and credits from `~/.cache/llm-usage.json` in Alfred.

The file is written every 10 minutes by ~/labs/llm-usage/llm-usage, run by the
com.shri.llm-usage LaunchAgent (~/lawn/launchd). One row per limit or credit;
Enter opens that provider's dashboard.
"""

import json
import math
import struct
import time
import zlib
from datetime import datetime
from pathlib import Path

DATA_FILE = Path.home() / ".cache" / "llm-usage.json"
LOG_FILE = Path.home() / "Library" / "Logs" / "llm-usage.log"
ICON_DIR = Path.home() / ".cache" / "llm-usage-icons"
ICON_SIZE = 64
# Supersampling per axis, for anti-aliased edges.
ICON_SS = 4
TRACK = (170, 170, 170, 110)
# Two missed runs of the 10-minute LaunchAgent.
STALE_SECS = 25 * 60
NAMES = {"anthropic": "Anthropic", "copilot": "Copilot", "deepinfra": "DeepInfra"}
# Credits with no limit of their own (prepaid balances) are drawn against this amount.
RING_FULL_USD = {"deepinfra": 50}


def parse_time(s):
	return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def human_duration(secs):
	mins = max(1, round(secs / 60))
	if mins < 60:
		return f"{mins}m"
	hours = mins // 60
	if hours < 48:
		return f"{hours}h {mins % 60}m" if mins % 60 else f"{hours}h"
	return f"{round(hours / 24)}d"


def ring_color(pct):
	if pct >= 80:
		return (230, 72, 60, 255)
	if pct >= 50:
		return (240, 170, 30, 255)
	return (10, 132, 255, 255)


def write_png(path, size, pixels):
	def chunk(kind, data):
		return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

	raw = b"".join(b"\0" + bytes(c for px in pixels[y * size:(y + 1) * size] for c in px) for y in range(size))
	png = (b"\x89PNG\r\n\x1a\n"
		+ chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
		+ chunk(b"IDAT", zlib.compress(raw, 9))
		+ chunk(b"IEND", b""))
	tmp = path.with_suffix(".tmp")
	tmp.write_bytes(png)
	tmp.replace(path)


def ring_icon(pct):
	"""Path to a ring chart PNG filled clockwise from 12 o'clock to `pct`, drawn once and cached."""
	pct = max(0, min(100, round(pct)))
	path = ICON_DIR / f"ring-{pct}.png"
	if path.exists():
		return str(path)

	color = ring_color(pct)
	outer, inner = ICON_SIZE * 0.47, ICON_SIZE * 0.32
	centre = ICON_SIZE / 2
	pixels = []
	for y in range(ICON_SIZE):
		for x in range(ICON_SIZE):
			fill = track = 0
			for sy in range(ICON_SS):
				for sx in range(ICON_SS):
					dx = x + (sx + 0.5) / ICON_SS - centre
					dy = y + (sy + 0.5) / ICON_SS - centre
					if not inner <= math.hypot(dx, dy) <= outer:
						continue
					angle = math.atan2(dx, -dy) % (2 * math.pi)
					if angle / (2 * math.pi) * 100 < pct:
						fill += 1
					else:
						track += 1
			n = ICON_SS * ICON_SS
			alpha = (fill * color[3] + track * TRACK[3]) / n
			if alpha == 0:
				pixels.append((0, 0, 0, 0))
				continue
			# Colour weighted by each part's contribution to the alpha.
			wf, wt = fill * color[3], track * TRACK[3]
			pixels.append(tuple(round((color[i] * wf + TRACK[i] * wt) / (wf + wt)) for i in range(3)) + (round(alpha),))

	ICON_DIR.mkdir(parents=True, exist_ok=True)
	write_png(path, ICON_SIZE, pixels)
	return str(path)


def segment_distance(px, py, ax, ay, bx, by):
	t = max(0, min(1, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
	return math.hypot(px - (ax + t * (bx - ax)), py - (ay + t * (by - ay)))


def stroke_icon(name, segments, color):
	"""Path to a PNG of thick round-ended strokes, drawn once and cached.

	`segments` are ((x1, y1), (x2, y2)) pairs in 0..1 icon coordinates.
	"""
	path = ICON_DIR / f"{name}.png"
	if path.exists():
		return str(path)

	half_width = ICON_SIZE * 0.07
	segs = [(ax * ICON_SIZE, ay * ICON_SIZE, bx * ICON_SIZE, by * ICON_SIZE) for (ax, ay), (bx, by) in segments]
	pixels = []
	for y in range(ICON_SIZE):
		for x in range(ICON_SIZE):
			covered = sum(
				any(segment_distance(x + (sx + 0.5) / ICON_SS, y + (sy + 0.5) / ICON_SS, *s) <= half_width for s in segs)
				for sy in range(ICON_SS)
				for sx in range(ICON_SS)
			)
			pixels.append(color[:3] + (round(color[3] * covered / (ICON_SS * ICON_SS)),))

	ICON_DIR.mkdir(parents=True, exist_ok=True)
	write_png(path, ICON_SIZE, pixels)
	return str(path)


def status_icon(ok):
	if ok:
		return stroke_icon("status-ok", [((0.18, 0.52), (0.4, 0.74)), ((0.4, 0.74), (0.82, 0.28))], (40, 190, 80, 255))
	return stroke_icon("status-failed", [((0.24, 0.24), (0.76, 0.76)), ((0.76, 0.24), (0.24, 0.76))], (230, 72, 60, 255))


def until(s, verb, now):
	if not s:
		return "no expiry"
	t = parse_time(s)
	return f"{verb} in {human_duration(t - now)} ({datetime.fromtimestamp(t):%a %d %b %H:%M})"


def rows(provider, data, now):
	name = NAMES.get(provider, provider)
	url = data.get("dashboard_url", "")
	# A failed provider still carries its last successful data, if it ever had any.
	for l in data.get("limits", []):
		used = f" · {l['used']:g}/{l['entitlement']:g}" if "entitlement" in l else ""
		yield {
			"title": f"{name} · {l['name']}: {l['used_pct']:g}% used{used}",
			"subtitle": until(l["resets_at"], "resets", now),
			"arg": url,
			"icon": {"path": ring_icon(l["used_pct"])},
		}
	for c in data.get("credits", []):
		of = f" of ${c['limit_usd']:g}" if c["limit_usd"] is not None else ""
		item = {
			"title": f"{name} · {c['name']}: ${c['remaining_usd']:.2f}{of} left",
			"subtitle": until(c["resets_at"], "ends", now),
			"arg": url,
		}
		full = c["limit_usd"] or RING_FULL_USD.get(provider)
		if full:
			item["icon"] = {"path": ring_icon(100 - c["remaining_usd"] / full * 100)}
		yield item
	if data.get("suspended"):
		yield {"title": f"{name}: account suspended", "subtitle": url, "arg": url}


def error_row(provider, data, now):
	name = NAMES.get(provider, provider)
	if "fetched_at" in data:
		t = parse_time(data["fetched_at"])
		shown = f"Showing data from {datetime.fromtimestamp(t):%H:%M} ({human_duration(now - t)} ago)"
	else:
		shown = "No data yet"
	return {
		"title": f"{name}: last update failed",
		"subtitle": f"{shown} · {data['error']}",
		"arg": data.get("dashboard_url", ""),
	}


def main():
	now = time.time()
	items = []
	if not DATA_FILE.exists():
		items.append({"title": f"{DATA_FILE} not found", "subtitle": "Is the com.shri.llm-usage LaunchAgent loaded?", "valid": False})
	else:
		d = json.loads(DATA_FILE.read_text())
		for provider, data in d["providers"].items():
			items.extend(rows(provider, data, now))
		for provider, data in d["providers"].items():
			if data["status"] != "ok":
				items.append(error_row(provider, data, now))
		fetched = parse_time(d["fetched_at"])
		age = now - fetched
		failed = sum(data["status"] != "ok" for data in d["providers"].values())
		if failed:
			result = f"Last run: {failed} of {len(d['providers'])} providers failed, see above"
		else:
			result = "Last run fully successful"
		if age > STALE_SECS:
			result = f"Stale, is the com.shri.llm-usage LaunchAgent running? {result}"
		items.append({
			"title": f"Updated {human_duration(age)} ago ({datetime.fromtimestamp(fetched):%H:%M})",
			"subtitle": f"{result} · Enter opens the log",
			"arg": str(LOG_FILE),
			# Stale data counts as a failure too: the numbers above may be out of date.
			"icon": {"path": status_icon(not failed and age <= STALE_SECS)},
		})
	print(json.dumps({"items": items}))


if __name__ == "__main__":
	main()
