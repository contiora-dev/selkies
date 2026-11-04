/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * The edge layout: the toolbar's bar pinned to an edge of the window, loaded
 * as a developer's bar, with the stream's live figures in the middle of it. It
 * starts on the top edge, and a button on it steps it clockwise to the right,
 * bottom, and left edges; a top or bottom bar is a row and a left or right
 * one a column of the same thickness. What it holds and how it opens are the
 * toolbar's: the toolbox button opens the overflow menu, the settings button
 * hangs the settings card against the bar, a panel that floats has a button
 * of its own, and the stats button lays the floating stats over the stream. The touch client's buttons and the soft
 * keys, opened from a button of the bar, are the toolbar's too.
 *
 * What a developer reaches for most rides the bar itself, never the menu:
 * the stream switches — the video, the audio, the microphone, and the
 * webcam — as toggles; the file and app dialogs and adding a second screen
 * as a button each; and the strip the sidebar's "Show over the stream" lays
 * over the stream — the four status marks, then the frame rate, the video
 * rate, and the time a frame takes to the wire, each a value over its
 * caption. Whatever edge the bar is pinned to, the strip rides top-center
 * over the stream, in the same spot and on the same dark ground the
 * sidebar's own strip takes, and the bar's own chrome knobs — the strip's
 * switch and the panels' translucency — sit among its buttons. The extra groups read the
 * catalog (`STREAMS`, `PANELS`) so their gates never fork from the menu's,
 * gates never fork from the menu's, which keeps the canvas the menu
 * already has (clipboard, sharing, shortcuts, printing) and the footer.
 * The bar's buttons and what they open are `panels/toolbox.tsx`, and which
 * of them is open, and the folding on Ctrl+Shift+M and gaming mode, is
 * `useBarState` (`layouts/actions.ts`), both shared with the toolbar. The
 * strip is the floating stats drawn for a bar (`StreamStats`' `bar` prop in
 * `panels/stats.tsx`). Mounting it is what turns the stats on, so the bar
 * mounts it only while the page may show stats at all.
 *
 * What this layout adds is where the bar is: pinned to an edge, with a tab on
 * that edge that brings it back once folded. The edge is kept per browser
 * (`model.ts`). Like the other layouts it floats over the stream and leaves
 * the core's sizing alone.
 * @module
 */
import * as React from "react";
import { ScreenShare } from "lucide-react";
import { ButtonGroup } from "@/components/ui/button-group";
import { cn } from "@/lib/utils";
import { useElementSize } from "@/panels/anchor";
import { PANELS, STREAMS, usePanelContext } from "@/panels/catalog";
import { StreamStats } from "@/panels/stats";
import { BarLogo, FloatingToolPanels, GamingButton, MainButtons, SettingsPopup, SoftKeysPanel, Tool, ToolboxMenu, TouchButtons } from "@/panels/toolbox";
import { useDashboard } from "@/state/dashboard";
import { t } from "@/i18n";
import { useActions, useBarPrefs, useBarState } from "../actions";
import { BAR_SIZE, PLACEMENT_SPECS, barStyle, nextPlacement, popupStyle, usePlacement } from "./model";

/** The bar, and the panels hanging from it. */
export default function EdgeLayout() {
  const d = useDashboard();
  const ctx = usePanelContext();
  const bar = useBarState();
  const { barStrip, translucency } = useBarPrefs();
  const { softKeys } = useActions();
  const [placement, setPlacement] = usePlacement();
  const barRef = React.useRef<HTMLDivElement>(null);
  const barSize = useElementSize(barRef, { width: BAR_SIZE, height: BAR_SIZE });

  const spec = PLACEMENT_SPECS[placement];
  const orientation = spec.vertical ? "vertical" : "horizontal";

  if (bar.collapsed) {
    return (
      <button type="button" aria-label={t("topMenu.showToolbar")} title={t("topMenu.showToolbar")} onClick={() => bar.setCollapsed(false)}
        className={cn("fixed z-[2000] flex items-center justify-center border bg-background text-muted-foreground hover:text-foreground", spec.restore)}>
        <spec.restoreIcon className="size-3" />
      </button>
    );
  }

  const side = spec.inward;
  // The menu's everyday actions as buttons of their own: the stream switches,
  // gated exactly as the menu gates them, so the two never fork.
  const r = d.renderable;
  const primary = !d.isSecondaryDisplay;
  const showStats = primary && r.stats;
  const streamActions = primary && r.coreButtons ? STREAMS.filter((stream) => !stream.input && stream.allowed(r)) : [];
  // The dialog panels (files, apps) and adding a second screen, each a button.
  const dialogActions = PANELS.filter((panel) => panel.dialog && panel.shown(ctx, "menu"));
  const addScreen = primary && r.secondScreen;
  // The edge a move button sends the bar to, named by its icon and tooltip as the layout toggle names the next layout.
  const target = PLACEMENT_SPECS[nextPlacement(placement)];

  return (
    <>
      <div ref={barRef} className={cn("edge fixed z-[2000] flex bg-background shadow-lg", spec.bar)} style={barStyle(placement)}>
        <BarLogo className="shrink-0" />

        <ToolboxMenu open={bar.menuOpen} onOpenChange={bar.onMenuOpenChange} side={side} tooltipSide={side} />

        {streamActions.length > 0 && (
          <ButtonGroup orientation={orientation}>
            {streamActions.map((stream) => (
              <Tool key={stream.id} side={side} label={t(stream.on(d) ? stream.disable : stream.enable)} active={stream.on(d)} className={`stream-${stream.id}-button`} onClick={() => stream.toggle(d)}>
                <stream.icon className="size-4" />
              </Tool>
            ))}
          </ButtonGroup>
        )}

        <MainButtons bar={bar} side={side} orientation={orientation} />

        {(dialogActions.length > 0 || addScreen) && (
          <ButtonGroup orientation={orientation}>
            {dialogActions.map((panel) => (
              <Tool key={panel.id} side={side} label={t(panel.title)} className={`${panel.id}-button`} onClick={() => panel.dialog && d.openDialog(panel.dialog)}>
                {panel.icon && <panel.icon className="size-4" />}
              </Tool>
            ))}
            {addScreen && (
              <Tool side={side} label={t('sections.screen.addScreenTitle')} className="add-screen-button" onClick={d.addScreen}>
                <ScreenShare className="size-4" />
              </Tool>
            )}
          </ButtonGroup>
        )}

        <GamingButton side={side} />

        <TouchButtons bar={bar} side={side} orientation={orientation} />

        <div className="flex min-h-0 min-w-0 flex-1 items-center justify-center gap-2 overflow-hidden" />

        <Tool side={side} label={t(target.moveKey)} onClick={() => { bar.fold(); setPlacement(nextPlacement(placement)); }}><target.moveIcon className="size-4" /></Tool>
        <Tool side={side} label={t('topMenu.hideToolbar')} onClick={bar.hide}><spec.hideIcon className="size-4" /></Tool>
      </div>

      <SettingsPopup open={bar.settingsOpen} onClose={bar.closeSettings} barRef={barRef} style={popupStyle(placement, barSize)} className={spec.popup} />

      {/* The strip's own spot whatever edge the bar pins to: top-center over
          the stream, on the dark ground the sidebar's strip takes. */}
      {showStats && barStrip && (
        <div className={cn("dark fixed top-2 left-1/2 z-[2040] flex max-w-[calc(100vw-1rem)] -translate-x-1/2 items-center justify-center rounded-md px-2.5 py-1 shadow-lg chrome-panel",
          ["bg-black/70", "bg-black/55", "bg-black/45", "bg-black/35"][translucency])}>
          <StreamStats bar />
        </div>
      )}

      <FloatingToolPanels open={bar.floating} onClose={bar.toggleFloating} />

      <SoftKeysPanel open={softKeys && bar.softKeysOpen}
        style={{ left: placement === "left" ? BAR_SIZE + 16 : 16, bottom: placement === "bottom" ? BAR_SIZE + 16 : 16 }} />
    </>
  );
}
