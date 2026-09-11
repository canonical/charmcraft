# Bug Report for craft-providers

**To be filed at:** https://github.com/canonical/craft-providers/issues

## Title
snapd "daemon is stopping to wait for socket activation" error during LXD container initialization

## Summary
When craft-providers creates and initializes LXD base containers, it fails with "daemon is stopping to wait for socket activation" error when attempting to wait for snap refreshes. This causes builds to fail intermittently.

## Environment
- Container OS: Ubuntu 22.04 (core22)
- Host OS: Ubuntu 20.04 (in spread tests)
- craft-providers version: ~3.1 (as used by charmcraft 4.0.0)
- Affected method: `craft_providers.base._disable_and_wait_for_snap_refresh`

## Steps to Reproduce
1. Set up LXD on an Ubuntu system
2. Use craft-providers (via charmcraft or directly) to create a new base LXD container from Ubuntu 22.04
3. The failure occurs during base container setup when craft-providers runs:
   ```bash
   snap watch --last=auto-refresh?
   ```

## Expected Behavior
The container should be created successfully, with snapd fully initialized and ready to handle snap operations.

## Actual Behavior
The command fails with:
```
error: daemon is stopping to wait for socket activation
craft_providers.lxd.errors.LXDError: Failed to wait for snap refreshes to complete.
```

## Error Details

### Error message:
```
error: daemon is stopping to wait for socket activation
craft_providers.lxd.errors.LXDError: Failed to wait for snap refreshes to complete.
* Command that failed: "lxc --project charmcraft exec local:base-instance-charmcraft-buildd-base-v71-3e75872519c3ea8f5604 -- env CRAFT_MANAGED_MODE=1 ... snap watch '--last=auto-refresh?'"
* Command exit code: 1
* Command standard error output: b'error: daemon is stopping to wait for socket activation\n'
```

### Full stack trace:
```python
File "/snap/charmcraft/x1/lib/python3.12/site-packages/craft_providers/base.py", line 616, in _disable_and_wait_for_snap_refresh
    executor.execute_run(
        ["snap", "watch", "--last=auto-refresh?"],
        capture_output=True,
        check=True,
    )
File "/snap/charmcraft/x1/lib/python3.12/site-packages/craft_providers/lxd/lxd_instance.py", line 267, in execute_run
    return self.lxc.exec(
File "/snap/charmcraft/x1/lib/python3.12/site-packages/craft_providers/lxd/lxc.py", line 528, in exec
    return runner(final_cmd, timeout=timeout, check=check, **kwargs)
File "/snap/charmcraft/current/usr/lib/python3.12/subprocess.py", line 571, in run
    raise CalledProcessError(retcode, process.args, output=stdout, stderr=stderr)
subprocess.CalledProcessError: Command [...] returned non-zero exit status 1.

The above exception was the direct cause of the following exception:

File "/snap/charmcraft/x1/lib/python3.12/site-packages/craft_providers/base.py", line 623, in _disable_and_wait_for_snap_refresh
    raise BaseConfigurationError(
        f"Failed to wait for snap refreshes to complete.\n"
        f"* Command that failed: {' '.join(cmd)!r}\n"
        f"* Command exit code: {error.returncode}\n"
        f"* Command standard error output: {error.stderr!r}"
    ) from error
craft_providers.errors.BaseConfigurationError: Failed to wait for snap refreshes to complete.
```

## Root Cause Analysis

The error "daemon is stopping to wait for socket activation" indicates that snapd inside the newly created container is in a transitional state. This typically happens when:

1. **Socket activation is pending**: snapd.socket is enabled but the daemon hasn't fully started yet
2. **Service is restarting**: The daemon is transitioning between states
3. **Race condition**: snap commands are being executed before snapd is fully operational

The current code in `craft_providers.base._disable_and_wait_for_snap_refresh()` (around line 616) doesn't handle this transient state, causing the entire container setup to fail.

## Impact

- **Build failures**: Causes charmcraft builds to fail intermittently
- **CI/CD failures**: Affects spread tests in charmcraft (e.g., smoketests/reactive, smoketests/different-dir)
- **Reproducibility issues**: Intermittent nature makes it hard to debug and reproduce consistently
- **Broader impact**: Affects any project using craft-providers to create fresh LXD containers

## Proposed Solutions

### Option 1: Add retry logic with exponential backoff (Recommended)

Modify `_disable_and_wait_for_snap_refresh` to retry when encountering the "daemon is stopping" error:

```python
def _disable_and_wait_for_snap_refresh(self, executor: Executor) -> None:
    """Disable and wait for snap refreshes with retry logic."""
    # ... existing code for snap refresh --hold ...
    
    # Wait for pending snap refreshes with retry
    max_retries = 5
    for attempt in range(max_retries):
        try:
            executor.execute_run(
                ["snap", "watch", "--last=auto-refresh?"],
                capture_output=True,
                check=True,
            )
            break  # Success
        except subprocess.CalledProcessError as error:
            stderr = error.stderr or b""
            if b"daemon is stopping" in stderr and attempt < max_retries - 1:
                # Transient snapd state, retry with exponential backoff
                wait_time = 2 ** attempt
                logger.debug(
                    f"snapd is in transitional state, retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
                continue
            # Non-transient error or max retries exceeded
            raise BaseConfigurationError(...) from error
```

### Option 2: Ensure snapd is fully ready before snap operations

Add preliminary checks to ensure snapd is operational before running snap commands:

```python
def _ensure_snapd_ready(self, executor: Executor) -> None:
    """Ensure snapd service is fully operational."""
    # Wait for snapd service to be active
    executor.execute_run(
        ["systemctl", "is-active", "snapd.service"],
        check=True,
    )
    
    # Wait for snap seed to be loaded
    executor.execute_run(
        ["snap", "wait", "system", "seed.loaded"],
        check=True,
    )
    
    # Small grace period for snapd to be fully ready
    time.sleep(2)
```

Then call this before `_disable_and_wait_for_snap_refresh`.

### Option 3: Graceful degradation

Make the snap refresh waiting non-fatal with a warning:

```python
try:
    executor.execute_run(["snap", "watch", "--last=auto-refresh?"], ...)
except subprocess.CalledProcessError as error:
    if b"daemon is stopping" in (error.stderr or b""):
        logger.warning(
            "snapd is in transitional state during container setup. "
            "Snap refreshes may not be fully disabled."
        )
        # Continue without failing
        return
    raise
```

## Additional Context

### Log excerpt from failing build:
```
2025-12-06 07:57:20.946 Executing in container: ... systemctl restart snapd.service
2025-12-06 07:57:21.577 Executing in container: ... snap wait system seed.loaded
2025-12-06 07:57:26.101 Holding refreshes for snaps.
2025-12-06 07:57:26.101 Executing in container: ... snap refresh --hold
2025-12-06 07:57:26.360 Waiting for pending snap refreshes to complete.
2025-12-06 07:57:26.360 Executing in container: ... snap watch '--last=auto-refresh?'
2025-12-06 07:57:26.602 Failed to wait for snap refreshes to complete.
```

The sequence shows that even after `systemctl restart snapd.service` and `snap wait system seed.loaded`, the subsequent `snap watch` command fails. This suggests the current synchronization mechanism is insufficient.

## References

- **Original failure**: https://github.com/canonical/charmcraft/actions/runs/19982288239/job/57318843865
- **Investigation PR**: https://github.com/canonical/charmcraft/pull/2509
- **Affected code**: `craft_providers/base.py`, method `_disable_and_wait_for_snap_refresh` (around line 616)

## Recommended Action

Implement **Option 1** (retry logic with exponential backoff) as it:
- Handles the transient nature of the error elegantly
- Doesn't require changing the overall flow
- Provides logging for debugging
- Has a reasonable timeout/retry limit
- Is a minimal, focused change

This should resolve the intermittent failures while maintaining robustness.
