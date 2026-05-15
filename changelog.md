# Changelog

All notable changes to this project will be documented in this file.

## [2026-05-05]

### Fixed
- **Ghost Device Bug (Admin Bypass)**: Fixed an issue where disconnected phones were still being tracked as "Present" when the program was not run as an Administrator.
  - Previously, the system relied on `arp -d *` to clear the Windows ARP cache, which silently failed without Administrator privileges, leaving stale, disconnected phones in the tracking loop.
  - The attendance scanner now strictly filters out devices by verifying if they actively replied to the background ICMP ping sweep (`ping.exe` exit code `0`). This ensures perfect detection accuracy and instant disconnect recognition, entirely bypassing the need to clear the Windows ARP cache or run as Administrator.
- **Strict Disconnect Policy**: Fixed an issue where a student could disconnect before reaching full attendance and still retain a "Partial" status forever.
  - Modified the status logic: if a student is marked "Partial" but disconnects before crossing the "Full Attendance" threshold, their status will now revert to "Absent". Once they reach "Full Attendance", their status becomes permanently "Present".
- **Inaccurate Timer Accumulation**: Fixed an issue where the tracked connection time was much slower than real-time ("it counts more").
  - Increased the tolerance window for continuous connection tracking from `10s` to `30s` in `update_sessions`. This accounts for the variable execution time of the background ping sweep, ensuring students are credited exact real-time seconds for their attendance instead of fixed 5-second intervals.

## [2026-05-04]

### Changed
- **Partial Attendance Units**: Updated the UI and backend to support "Minutes" instead of "Hours" for partial attendance thresholds.
  - Modified `admin.html` to replace the "Hours" option with "Minutes" in the partial attendance unit dropdown.
  - Updated `main.py`'s `calculate_status` function to correctly handle the `minutes` unit for partial attendance threshold calculations.
- **Backend Logic**: Refactored the threshold calculation for better readability and extensibility.
