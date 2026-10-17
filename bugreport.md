# VectorMachine Bug Report

**Date:** 2026-10-17
**Branch analysed:** `Fix` @ `3fd02df`
**Scope:** All of `src/`, `tests/`, `test_debug.py`, `.github/workflows/ci.yml`, requirements and docs.

## How this was checked

- Read every source, test, CI and config file.
- Ran the local suite: `pytest` passed 47/47 and `ruff check .` was clean (Python 3.14.6, offscreen Qt).
- Wrote throwaway probe scripts (not committed) to reproduce each runtime finding below against the real modules. Findings marked **Confirmed** were reproduced; **Code review** findings come from reading the code only.
- Pulled the last CI run on `Fix` (run `34052049338`, failed) and read its logs.

The test suite passes, but it doesn't exercise any of the paths below.

## Summary

| # | Severity | Area | Title | Status |
|---|----------|------|-------|--------|
| 1 | High | Parser | `^` is parsed as XOR: `2^3` silently becomes `1`, and `x^2` is rejected | **Fixed** |
| 2 | High | Parser / UI | Large integer literals (`9**9**9`) freeze the GUI thread for good | **Fixed** |
| 3 | High | Visualization | Fields with `P = 0` never render | **Fixed** |
| 4 | High | Compute UI | A stale worker signal clobbers the active computation, and its result is dropped | **Fixed** |
| 5 | High | CI | Every Linux job and every Python 3.11 job fails, and the Windows install step hides pip errors | **Fixed** |
| 6 | Medium | Compute worker | Timeout and cancel don't stop work: orphan threads burn CPU and hold up app exit | **Fixed** |
| 7 | Medium | Results / Export | The panel shows only the latest result, so PDF and TXT/MD exports disagree | **Fixed** |
| 8 | Medium | Visualization | Changing the scale slider with keyboard, wheel or a groove click never redraws | **Fixed** |
| 9 | Medium | Sessions | Loaded results are shown without checking they match the loaded field | Code review |
| 10 | Medium | Visualization | Fields using `!` (factorial) parse fine but can't be plotted (cryptic error) | Confirmed |
| 11 | Medium | Visualization | Arrow scale is absolute; 2D mode still plots the out-of-plane `w` component | Code review |
| 12 | Medium | Concurrency | Visualization workers pile up and share an unlocked `OrderedDict` cache | Code review |
| 13 | Low | Input UI | At startup all three fields show the red error "Expression cannot be empty." | Confirmed |
| 14 | Low | Theming | Hard-coded colours ignore the dark theme | Code review |
| 15 | Low | Parser | Scientific notation (`1e3`) is rejected as "Unsupported name: e3" | Confirmed |
| 16 | Low | Core | `_lazy_init()` is not thread-safe (latent) | Code review |
| 17 | Low | Visualization | A VTK init failure is permanent for the whole session | Code review |
| 18 | Low | Repo / Docs | Tracked build debris, a stray spike file, and docs that no longer match the code | Confirmed |

---

## 1. `^` is parsed as XOR: `2^3` silently becomes `1`, and `x^2` is rejected — High — **Fixed**

**Where:** [computation.py:23](src/core/computation.py:23), [computation.py:90](src/core/computation.py:90)

The allowed-character regex accepts `^`, but the transformation list is `standard_transformations + (implicit_multiplication_application,)`. That list does not include `convert_xor`, so `^` keeps its Python meaning, bitwise XOR.

**Repro (probe output):**

```
'x^2'      -> None  Syntax Error: unsupported operand type(s) for ^: 'Symbol' and 'Integer'
'2^3'      -> 1     (no error; 2 XOR 3 == 1)
'sin^2(x)' -> None  Syntax Error: unsupported operand type(s) for ^: 'FunctionClass' and 'Mul'
```

Most students type `^` for powers. A purely numeric power such as `2^3*x` gives a wrong answer with no warning, and a symbolic power such as `x^2` gives a confusing Python error.

**Fix:** add `convert_xor` to the transformations (`from sympy.parsing.sympy_parser import convert_xor`). Add tests for `x^2 == x**2` and `2^3 == 8`.

## 2. Large integer literals (`9**9**9`) freeze the GUI thread for good — High — **Fixed**

**Where:** [input_panel.py:486-488](src/ui/input_panel.py:486) calls `parse_expression` on the GUI thread; [computation.py:91](src/core/computation.py:91)

`parse_expr` evaluates integer arithmetic eagerly. `9**9**9` is `9**387420489`, a bignum with about 370 million digits. CPython computes it inside one C call that holds the GIL, so:

- the Qt event loop stops 400 ms after the user stops typing (the debounce), and the OS reports the window as not responding;
- no other Python thread can run either. In the probe, a `Thread.join(5)` watchdog never got control back, and the process was still stuck when it was killed at 60 s.

The 10-second `ComputeWorker` timeout can't help here. It runs on the wrong thread, and a GIL-holding C call can't be interrupted anyway. The same applies to `(10**8)!`.

**Fix:** before parsing, reject inputs whose numeric literals or `**` chains exceed a bound. For example, walk the token stream and reject a power whose exponent literal is above about 1000, or call `parse_expr(..., evaluate=False)` and inspect `Pow` nodes before calling `.doit()`. Also consider moving validation off the GUI thread.

## 3. Fields with `P = 0` never render — High — **Fixed**

**Where:** [visualization_panel.py:213](src/ui/visualization_panel.py:213)

```python
def _do_update_plot(self):
    if not self.p_expr:
        return
```

`bool(sympy.Integer(0))` is `False`, so any field whose first component is `0` exits early and leaves the plot blank. That includes `<0, x, 0>`, `<0, 0, 1>` and `<0, -z, y>`, which are common textbook examples.

**Repro:** `field ('0','x','0') worker started: False` / `field ('x','0','0') worker started: True`.

**Fix:** `if self.p_expr is None:`. Add a regression test.

## 4. A stale worker signal clobbers the active computation, and its result is dropped — High — **Fixed**

**Where:** [app_window.py:264-287](src/ui/app_window.py:264)

`_on_compute_finished` and `_on_compute_error` don't check which worker sent the signal. They unconditionally clear `_compute_in_progress`, `_compute_worker` and `_active_compute_revision`.

`ComputeWorker.run` checks `_cancelled` and then emits a queued signal. If worker A emits just before the user clicks **Cancel** and then **Compute** again (worker B), A's queued signal arrives while B is running. Then:

1. The state is reset: buttons re-enable while B is still running, so a third worker can start.
2. `_active_compute_revision` is now `None`, so when B finishes, `is_current` is `False` and **B's real result is thrown away without any message**.

**Repro (probe output):**

```
after stale signal: in_progress = False | B running: True | buttons enabled: True
B's curl result shown: False
```

**Fix:** pass the worker to the slot, for example `worker.finished_ok.connect(lambda t, r, w=worker: self._on_compute_finished(w, t, r))`, and return early when `w is not self._compute_worker`. `_cancel_compute_worker` already sets `_compute_worker = None`, so this check is enough. Apply the same pattern to `VisualizationPanel`, which is already protected by `revision_id`.

## 5. Every Linux job and every Python 3.11 job fails, and the Windows install step hides pip errors — High — **Fixed**

**Where:** [ci.yml:45](.github/workflows/ci.yml:45), [ci.yml:66](.github/workflows/ci.yml:66), [ci.yml:72-76](.github/workflows/ci.yml:72), [requirements.txt](requirements.txt)

The last run on `Fix` (`34052049338`) failed in 3 of its 4 test jobs:

- **Ubuntu:** `E: Package 'libgl1-mesa-glx' has no installation candidate`. That package was removed in Ubuntu 24.04, which is what `ubuntu-latest` now uses. Both Linux jobs stop before installing anything.
- **Python 3.11:** `numpy==2.5.1 Requires-Python >=3.12`. `pip index versions numpy --python-version 3.11` confirms 2.4.6 is the newest version available for 3.11.
- **Masked failure on Windows:** the multi-line `run:` block under PowerShell only reports the exit code of its last command. "Install project dependencies" showed ✓ even though `pip install -r requirements.txt` had failed, and the job then broke later at `ImportError while loading conftest`.

Only Windows / Python 3.12 is green.

**Fix:** remove `libgl1-mesa-glx` (keep `libgl1`, `libegl1`, `libglx-mesa0`, `xvfb`). Either drop 3.11 from the matrix or relax the pins (for example `numpy>=2.2,<3`). Add `shell: bash` (or `$ErrorActionPreference='Stop'` with per-line checks) to the install step. Also update the README, which still says "Python 3.9+".

**Resolution:** the workflow now pins `ubuntu-24.04` / `windows-2025`, installs `libgl1` instead of the removed `libgl1-mesa-glx`, tests Python 3.12 and 3.14 (the pins need ≥ 3.12), runs every test step under `bash` so a failing command fails its step, and bumps the official actions to `v7` (Node 24). The README now says Python 3.12+. Verified by run `39053140611`: lint and all four test jobs passed, each running all 52 tests.

## 6. Timeout and cancel don't stop work: orphan threads burn CPU and hold up app exit — Medium — **Fixed**

**Where:** [compute_worker.py:39-56](src/ui/compute_worker.py:39); no `closeEvent` in [app_window.py](src/ui/app_window.py)

`future.result(timeout=...)` returns to the caller, but the `ThreadPoolExecutor` thread keeps running SymPy. `shutdown(wait=False, cancel_futures=True)` only cancels futures that haven't started yet. Each timeout or cancel therefore leaves a thread spinning at 100% of a core. `concurrent.futures` joins its worker threads at interpreter exit, so **closing the app hangs until every runaway `simplify()` returns**.

**Repro:** a worker with `timeout_sec=0.3` and a 6-second computation: the worker reported a timeout at once, but the process took **7 s** to exit.

The window also has no `closeEvent` that cancels or waits for `ComputeWorker` and `VisualizationWorker` threads, which are children of the window.

**Fix:** run the SymPy call in a `multiprocessing` / `ProcessPoolExecutor` child that can be terminated, or at minimum use a daemon thread. Add a `closeEvent` that cancels both kinds of worker and calls `wait()` with a short bound.

**Resolution:** SymPy now runs in a long-lived child process (`src/core/compute_process.py`), which is killed on timeout or cancel and replaced on the next request. The app pre-spawns it at startup, so the first computation starts warm. `VectorMachineWindow.closeEvent` cancels compute and visualization workers and waits for them, with a bounded wait. Regression tests cover timeout, cancel, closing the window during a computation, and exit not being delayed.

## 7. The panel shows only the latest result, so PDF and TXT/MD exports disagree — Medium — **Fixed**

**Where:** [results_panel.py:385-389](src/ui/results_panel.py:385), [app_window.py:369-374](src/ui/app_window.py:369)

`display_divergence` and `display_curl` each call `setHtml`, which replaces whatever was there. After **Compute Divergence** and then **Compute Curl**:

- the panel shows only curl, although `last_div_steps` is still kept (confirmed: `last_div kept: True | divergence still visible after curl: False`);
- TXT and MD exports contain **both** results, because they read `last_*_steps`;
- PDF and PNG exports contain **only curl**, because they read the panel HTML.

**Fix:** have the compute handlers call `display_results(self.last_div_steps, self.last_curl_steps)`, the same method session load already uses.

**Resolution:** the compute handlers now call `display_results(self.last_div_steps, self.last_curl_steps)`.

## 8. Changing the scale slider with keyboard, wheel or a groove click never redraws — Medium — **Fixed**

**Where:** [visualization_panel.py:100](src/ui/visualization_panel.py:100)

Only `sliderReleased` is connected. Keyboard input (arrow keys, PageUp/PageDown), the mouse wheel and clicks on the groove change the value without emitting `sliderReleased`.

**Repro:** after `PageUp`, the slider value went from 20 to 30 and no redraw was scheduled. The README advertises keyboard accessibility.

**Fix:** connect `valueChanged` as well; the 300 ms `plot_timer` debounce already absorbs drags. Alternatively, connect `valueChanged` only when `not slider.isSliderDown()`.

**Resolution:** `valueChanged` now schedules a redraw unless the slider is being dragged; drags still redraw once, on `sliderReleased`.

## 9. Loaded results are shown without checking they match the loaded field — Medium

**Where:** [app_window.py:342-346](src/ui/app_window.py:342), [session.py:28-40](src/core/session.py:28)

The session stores pre-rendered result strings next to `P`, `Q` and `R`. Validation only checks that the expected keys exist and hold strings. On load, the results are displayed and kept in `last_*_steps`, so they are also exported, even when:

- the saved results don't belong to the saved field (the file was hand-edited, merged, or saved by an older buggy build), or
- the loaded field doesn't parse (the compute buttons are disabled, but the results still look authoritative).

The session format also has no `version` field.

**Fix:** on load, discard the saved results and recompute from `P`, `Q` and `R` (it's cheap), or at least store a hash of the parsed inputs and drop results that don't match. Add `"version": 1`.

## 10. Fields using `!` (factorial) parse fine but can't be plotted (cryptic error) — Medium

**Where:** [computation.py:109](src/core/computation.py:109) (`lambdify(..., modules='numpy')`)

`x!` passes validation and the symbolic computation works. Plotting it raises `TypeError: only integer scalar arrays can be converted to a scalar index`, which the user sees as a raw "Visualization Error" dialog. The other whitelisted functions all evaluate correctly (checked: `sign`, `floor`, `ceiling`, `Abs`, `atan2`, `sqrt`, `log`, `E`, constants).

**Fix:** lambdify with `modules=['numpy', 'scipy']` and map `factorial` to `scipy.special.gamma(x+1)`, or catch it and show "factorial can't be plotted".

## 11. Arrow scale is absolute; 2D mode still plots the out-of-plane `w` component — Medium

**Where:** [visualization_panel.py:305](src/ui/visualization_panel.py:305), [visualization_worker.py:50-68](src/ui/visualization_worker.py:50)

- `cloud.glyph(scale="magnitude", factor=scale_factor)` makes arrow length equal to `|F| × factor` in world units, with no reference to grid spacing or the field's maximum. With the default domain ±5 and `F = <x², y², z²>`, arrows reach about 15 units long in a 10-unit box. Near singularities (`1/x`), a few arrows grow huge and the rest shrink to dots. Normalise by `max(|F|)`, or by a robust percentile, times the grid spacing.
- In **2D** mode the grid lies on `z = 0`, but the vectors keep `w` and the magnitude includes it. A "2D quiver" of `<-y, x, 1>` shows arrows tilted out of the plane, viewed from straight above. Zero `w` in 2D mode.

## 12. Visualization workers pile up and share an unlocked `OrderedDict` cache — Medium

**Where:** [visualization_panel.py:226-264](src/ui/visualization_panel.py:226), [computation.py:103-113](src/core/computation.py:103)

`_cancel_active_worker` only sets a flag. A worker already inside `evaluate_field` keeps running, and every change to a spinbox or radio button starts a new `QThread`. With a slow expression, threads accumulate. Several threads can then run `_get_lambdified` at once, and it does `pop`, insert and `popitem` on a module-level `OrderedDict` with no lock. That is a data race: at worst a `KeyError` from `popitem` on an empty dict, or a duplicate lambdify.

**Fix:** add a `threading.Lock` around the cache. Keep at most one viz worker running, and start the latest request only after the current one finishes.

## 13. At startup all three fields show the red error "Expression cannot be empty." — Low

**Where:** [input_panel.py:419](src/ui/input_panel.py:419), [input_panel.py:497-499](src/ui/input_panel.py:497)

`do_validate_inputs()` runs in `__init__`, so a fresh window opens with three red error labels. The same happens after **Clear**. Empty fields should show no error, only a disabled Compute button.

## 14. Hard-coded colours ignore the dark theme — Low

**Where:** [results_panel.py:410](src/ui/results_panel.py:410), [results_panel.py:424](src/ui/results_panel.py:424) (`color:blue`); [input_panel.py:430-511](src/ui/input_panel.py:430) (`red`, `green`, `#b36b00`); [visualization_panel.py:89](src/ui/visualization_panel.py:89) (`#666`); [visualization_panel.py:132](src/ui/visualization_panel.py:132) (white plot background)

Dark is the default theme. Pure blue on `#252526` has a contrast of about 2.4:1, which fails WCAG AA, and the white VTK viewport is jarring in dark mode. Take these colours from the theme module.

## 15. Scientific notation (`1e3`) is rejected as "Unsupported name: e3" — Low

**Where:** [computation.py:81-87](src/core/computation.py:81)

The identifier regex matches the `e3` in `1e3`. Either strip numeric literals before scanning for identifiers, or document that scientific notation isn't supported.

## 16. `_lazy_init()` is not thread-safe (latent) — Low

**Where:** [computation.py:29-44](src/core/computation.py:29)

The function publishes the global `sp` (line 38) before it assigns `x`, `y`, `z` and `local_dict` (lines 44-45). A second thread that sees `sp is not None` returns early and uses `x = None`. This can't happen in the app today, because the first non-empty parse always runs on the GUI thread before any worker exists. It would break library or CLI use with threads. Assign `sp` last, or guard the function with a lock.

## 17. A VTK init failure is permanent for the whole session — Low

**Where:** [visualization_panel.py:121-147](src/ui/visualization_panel.py:121)

`_vtk_initialization_failed` is set once and is never retried. There is no fallback renderer such as Matplotlib quiver, even though Matplotlib is already in `requirements.txt`. This was already listed in `Weakness.md` and is still open.

## 18. Tracked build debris, a stray spike file, and docs that no longer match the code — Low

- Twelve tracked `desktop.ini` files. Their deletion is the uncommitted work on `Fix` (see below).
- Seven tracked `__pycache__/*.cpython-314.pyc` files, although `.gitignore` already excludes `*.pyc`.
- `src/test_pv.py`, a throwaway VTK spike, is still in the production package. `Weakness.md` Phase 2 lists it for removal.
- `test_debug.py` is still in the repo root, duplicating `tests/`.
- `requirements.txt` is a full `pip freeze` that includes packages the app doesn't use (`cyclopts`, `rich`, `rich-rst`, `requests`, `markdown-it-py`, …).
- README: the clone URL is a placeholder (`yourusername`), and the "Step-by-Step Derivations" claim is overstated (Weakness §3.4).
- `doc/Progress.md` says repository hygiene is done, but the items above are still open.

---

## Suggested fix order

1. Items **1–4**: small, low-risk patches with large user impact. Each comes down to a one-line or few-line change plus a regression test.
2. Item **5**, so CI can catch regressions again.
3. Items **6–8**, the next most visible behaviour bugs.
4. The rest as cleanup.
