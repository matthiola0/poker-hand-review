@echo off
REM Launcher for n8-review's solver backend -> TexasSolver adapter.
REM n8-review calls: texassolver.cmd <input.json>  (no extra args), which this
REM forwards to the adapter. Set TEXAS_SOLVER_CONSOLE to your console_solver.exe.
python "%~dp0..\tools\texassolver_adapter.py" %*
