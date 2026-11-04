/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * What the edge layout decides apart from its markup: which edge of the
 * window the bar is pinned to, and where what opens from it is placed.
 *
 * The bar sits on one of four edges, and `PLACEMENT_SPECS` holds everything
 * that differs between them: whether the bar is a row or a column of the
 * same thickness, the classes that pin it, the side its menus and tooltips
 * open on, and the icons and dictionary key that name a move to it. The
 * component reads this table, so it never branches on the edge. The cycle a
 * move button steps through runs clockwise from the top. A bar that cannot
 * hold its tools across its edge wraps them to a second row or column of
 * the same thickness, so nothing condenses into a menu and nothing
 * scrolls; what opens from it hangs from its measured size, so a wrapped
 * bar never lies under them.
 *
 * The edge is kept per browser under the prefixed `edge_placement` key, so a
 * reload lands where the page was left; a page that has chosen none gets the
 * top.
 * @module
 */
import * as React from "react";
import { ArrowDownToLine, ArrowLeftToLine, ArrowRightToLine, ArrowUpToLine, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, type LucideIcon } from "lucide-react";
import type { Side } from "@/panels/toolbox";
import { getPrefixedKey } from "@/utils";

/** The edge of the window the bar is pinned to. */
export type Placement = "top" | "bottom" | "left" | "right";

/** Every placement in the order a move button cycles them, so a stored value is checked against literals. */
export const PLACEMENTS: Placement[] = ["top", "right", "bottom", "left"];

/** Thickness of the bar in pixels on every edge, so a column on a side edge is no thicker than a row on the top. */
export const BAR_SIZE = 32;

/** Pixels between the bar and what opens from it. */
const POPUP_GAP = 8;

/** How one placement is drawn. */
export interface PlacementSpec {
  /** The bar is a column on the left or right edge. */
  vertical: boolean;
  /** Classes that pin the bar to its edge and lay its contents out. */
  bar: string;
  /** The entry of what opens from the bar: it slides in from the bar's side. */
  popup: string;
  /** Classes of the tab that restores a folded bar. */
  restore: string;
  /** The side of a bar button its menu and tooltip open on, away from the edge. */
  inward: Side;
  /** The mark of the button that folds the bar away, and of the tab that brings it back. */
  hideIcon: LucideIcon;
  restoreIcon: LucideIcon;
  /** The mark and dictionary key of a move to this edge. */
  moveIcon: LucideIcon;
  moveKey: string;
}

export const PLACEMENT_SPECS: Record<Placement, PlacementSpec> = {
  top: {
    vertical: false,
    bar: "inset-x-0 top-0 flex-row flex-wrap items-center gap-1.5 border-b px-2",
    popup: "slide-in-from-top-2",
    restore: "top-0 left-1/2 h-4 w-12 -translate-x-1/2 rounded-b-md border-t-0",
    inward: "bottom",
    hideIcon: ChevronUp, restoreIcon: ChevronDown, moveIcon: ArrowUpToLine, moveKey: "layout.edgeMoveTop",
  },
  bottom: {
    vertical: false,
    bar: "inset-x-0 bottom-0 flex-row flex-wrap items-center gap-1.5 border-t px-2",
    popup: "slide-in-from-bottom-2",
    restore: "bottom-0 left-1/2 h-4 w-12 -translate-x-1/2 rounded-t-md border-b-0",
    inward: "top",
    hideIcon: ChevronDown, restoreIcon: ChevronUp, moveIcon: ArrowDownToLine, moveKey: "layout.edgeMoveBottom",
  },
  left: {
    vertical: true,
    bar: "inset-y-0 left-0 flex-col flex-wrap items-center gap-1.5 border-r py-2",
    popup: "slide-in-from-left-2",
    restore: "left-0 top-1/2 h-12 w-4 -translate-y-1/2 rounded-r-md border-l-0",
    inward: "right",
    hideIcon: ChevronLeft, restoreIcon: ChevronRight, moveIcon: ArrowLeftToLine, moveKey: "layout.edgeMoveLeft",
  },
  right: {
    vertical: true,
    bar: "inset-y-0 right-0 flex-col flex-wrap items-center gap-1.5 border-l py-2",
    popup: "slide-in-from-right-2",
    restore: "right-0 top-1/2 h-12 w-4 -translate-y-1/2 rounded-l-md border-r-0",
    inward: "left",
    hideIcon: ChevronRight, restoreIcon: ChevronLeft, moveIcon: ArrowRightToLine, moveKey: "layout.edgeMoveRight",
  },
};

/**
 * The placement a move button sends the bar to.
 * @param placement The edge the bar is on.
 * @returns The next edge clockwise.
 */
export function nextPlacement(placement: Placement): Placement {
  return PLACEMENTS[(PLACEMENTS.indexOf(placement) + 1) % PLACEMENTS.length];
}

/**
 * The style that sizes a bar: its minimum thickness across the edge, which
 * a wrapped second row or column grows past.
 * @param placement The edge the bar is on.
 */
export function barStyle(placement: Placement): React.CSSProperties {
  return PLACEMENT_SPECS[placement].vertical ? { minWidth: BAR_SIZE } : { minHeight: BAR_SIZE };
}

/**
 * The style that hangs a card against the bar, at the bar's start where the
 * wordmark, the toolbox, and the settings button are.
 * @param placement The edge the bar is on.
 * @param size The bar's measured box (`useElementSize`): its thickness on
 * the day it wraps, so the card hangs clear of both rows.
 */
export function popupStyle(placement: Placement, size: { width: number; height: number }): React.CSSProperties {
  const across = (PLACEMENT_SPECS[placement].vertical ? size.width : size.height) + POPUP_GAP;
  switch (placement) {
    case "top": return { top: across, left: POPUP_GAP };
    case "bottom": return { bottom: across, left: POPUP_GAP };
    case "left": return { left: across, top: POPUP_GAP };
    default: return { right: across, top: POPUP_GAP };
  }
}

/** Reads the stored placement: the one it names, else the top. */
function readPlacement(): Placement {
  const stored = localStorage.getItem(getPrefixedKey("edge_placement"));
  return PLACEMENTS.find((placement) => placement === stored) ?? "top";
}

/**
 * The edge the bar is pinned to, written back to storage as it changes.
 * @returns The placement and its setter.
 */
export function usePlacement(): [Placement, (placement: Placement) => void] {
  const [placement, setPlacement] = React.useState<Placement>(readPlacement);
  React.useEffect(() => { localStorage.setItem(getPrefixedKey("edge_placement"), placement); }, [placement]);
  return [placement, setPlacement];
}
