# GZLJ01 (twwgz.iso, JP) function addresses — from framework.map

⚠️ The decomp `tww/.inc` comment addresses are a DIFFERENT version (US/GZLE01).
The LIVE game is JP/GZLJ01. Use THESE (from the JP `framework.map`, a local TWW decomp/extract)
for any live breakpoint. Example mismatch: procSwimWait_init decomp=0x8013DB24 vs JP=0x8013a8a4.

| Function | JP addr | size | source |
|----------|---------|------|--------|
| daPy_lk_c::execute | 0x8011e750 | 0x14a0 | d_a_player_main.o |
| daPy_lk_c::setNormalSpeedF | 0x80105ae0 | 0x218 | d_a_player_main.o |
| daPy_lk_c::setSpeedAndAngleSwim | 0x801399e4 | 0x2c8 | d_a_player_main.o |
| daPy_lk_c::checkNextModeSwim | 0x80139cac | 0x94 | |
| daPy_lk_c::changeSwimProc | 0x80139d40 | 0x1f0 | |
| daPy_lk_c::setSwimMoveAnime | 0x8013a2b0 | 0x108 | |
| daPy_lk_c::getSwimTimerRate | 0x8013a3b8 | 0x80 | |
| daPy_lk_c::setSwimTimerStartStop | 0x8013a438 | 0x15c | |
| daPy_lk_c::procSwimUp_init | 0x8013a594 | 0x204 | |
| daPy_lk_c::procSwimUp | 0x8013a798 | 0x10c | |
| daPy_lk_c::procSwimWait_init | 0x8013a8a4 | 0x1b8 | |
| daPy_lk_c::procSwimWait | 0x8013aa5c | 0x1b0 | |
| daPy_lk_c::procSwimMove_init | 0x8013ac0c | 0xd4 | |
| daPy_lk_c::procSwimMove | 0x8013ace0 | 0x2f0 | |
| daPy_lk_c::setFrameCtrl | 0x80107c2c | 0x60 | |
| J3DFrameCtrl::init(s) | 0x802ed358 | 0x30 | J3DAnimation.cpp |
| J3DFrameCtrl::checkPass(f) | 0x802ed388 | 0x5a0 | J3DAnimation.cpp |
| J3DFrameCtrl::update() | 0x802ed928 | 0x43c | J3DAnimation.cpp |
| cLib_addCalc(Pf,f,f,f,f) | 0x80250074 | 0xc0 | c_lib.cpp |
| cM_scos(s) | 0x800ecfe8 | 0x1c | |
| cM_ssin(s) | 0x800ed004 | 0x1c | |

## Breakpoint mechanism (fork Python scripting, no rebuild needed for break-mode)
- `debug.set_breakpoint(addr)` → break_on_hit=TRUE, log_on_hit=FALSE (PAUSES core on hit; does NOT log regs).
- `debug.set_memory_breakpoint({At/Start/End, BreakOnRead, BreakOnWrite, LogOnHit, BreakOnHit, Condition})` — full flags (data watchpoint only, not instr fetch).
- On code-BP hit: CheckBreakPoints logs GPR3-12+LR to MEMMAP iff log_on_hit; CheckAndHandleBreakPoints emits CodeBreakpoint event then CPU().Break().
- `event.on_codebreakpoint(cb)` cb(addr); `event.on_memorybreakpoint(cb)` cb(is_write, addr, value); `registers.read_gpr(n)/read_fpr(n)`.
- To non-pausing call-trace a code addr (log_on_hit=true, break_on_hit=false) the single-arg debug.set_breakpoint is insufficient → would need a small rebuild to expose flags, OR use on_codebreakpoint+resume.
